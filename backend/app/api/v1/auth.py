from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SESSION_COOKIE, STATE_COOKIE, get_db
from app.core.config import get_settings
from app.core.ratelimit import limiter, user_key
from app.core.security import hash_session_token
from app.models.user import OAuthAccount, User
from app.models.user import Session as DbSession
from app.schemas.auth import DevLoginRequest
from app.services import audit_service, org_service
from app.services.session_service import create_session, revoke_session
from app.utils.ip import client_ip as _client_ip
from app.utils.username import sanitize_oauth_username

router = APIRouter(prefix="/auth", tags=["auth"])


def _provider_enabled(client_id: str, client_secret: str) -> bool:
    return bool(client_id.strip()) and bool(client_secret.strip())


@router.get("/providers")
@limiter.limit("60/minute")
async def auth_providers(request: Request) -> dict[str, bool]:
    """Report which sign-in methods are currently configured.

    The frontend uses this to only render the providers an operator has
    wired up — no "ghost" buttons that redirect to a 503.
    """

    s = get_settings()
    return {
        "google": _provider_enabled(s.google_client_id, s.google_client_secret),
        "github": _provider_enabled(s.github_client_id, s.github_client_secret),
        "gitlab": _provider_enabled(s.gitlab_client_id, s.gitlab_client_secret),
        "dev": s.enable_dev_auth,
    }


_STATE_MAX_AGE_S = 600
# Keep the session cookie in sync with the server-side sliding inactivity
# window so the browser never advertises credentials the server has already
# discarded.
_SESSION_COOKIE_MAX_AGE_S = 60 * 60 * 24 * 7


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="oauth-state")


class _OAuthStateError(Exception):
    """Raised internally when the OAuth state check fails."""


def _validate_oauth_state(request: Request, state: str) -> None:
    raw_state = request.cookies.get(STATE_COOKIE)
    if raw_state is None:
        raise _OAuthStateError("missing")
    try:
        expected = _state_serializer().loads(raw_state, max_age=_STATE_MAX_AGE_S)
    except (BadSignature, SignatureExpired) as exc:
        raise _OAuthStateError("invalid") from exc
    if expected != state:
        raise _OAuthStateError("mismatch")


def _login_error_redirect(reason: str) -> RedirectResponse:
    """Bounce the browser back to the login page with an error flag and
    actively clear the OAuth state cookie so it cannot be replayed."""

    settings = get_settings()
    target = f"{settings.frontend_origin.rstrip('/')}/#/login?error={reason}"
    redirect = RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie(STATE_COOKIE, path="/")
    return redirect


def _oauth_start_redirect(authorize_url: str, state: str) -> RedirectResponse:
    settings = get_settings()
    redirect = RedirectResponse(url=authorize_url)
    redirect.set_cookie(
        key=STATE_COOKIE,
        value=_state_serializer().dumps(state),
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=_STATE_MAX_AGE_S,
        path="/",
    )
    return redirect


async def _find_or_create_oauth_user(
    db: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
    suggested_username: str,
    avatar_url: str | None,
) -> User:
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    link = result.scalar_one_or_none()
    if link:
        user = await db.get(User, link.user_id)
        if user is None or user.is_deleted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing")
        return user

    fallback = f"{provider}_{provider_user_id}"
    base = sanitize_oauth_username(suggested_username, fallback=fallback)
    candidate = base
    suffix = 0
    while True:
        exists = await db.execute(select(User.id).where(User.username == candidate))
        if exists.scalar_one_or_none() is None:
            break
        suffix += 1
        # Keep room for the numeric suffix while still respecting max_length=64.
        candidate = f"{base[:50]}_{suffix}"[:64]

    is_first = await _is_first_user(db)
    user = User(
        username=candidate,
        bio="",
        avatar_url=avatar_url,
        is_deleted=False,
        is_superuser=is_first,
        can_create_orgs=is_first,
    )
    db.add(user)
    await db.flush()
    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
    )
    if is_first:
        await audit_service.record(
            db,
            action="admin.bootstrap.superuser",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            metadata={"reason": "first_user", "provider": provider},
        )
    await db.commit()
    await db.refresh(user)
    return user


async def _is_first_user(db: AsyncSession) -> bool:
    """Return True if no user currently exists (including soft-deleted).

    Used by dev + OAuth login to promote the very first account to super-user
    automatically. We count soft-deleted users too so a nuked admin cannot
    trigger a second auto-bootstrap by coming back in.
    """

    from sqlalchemy import func

    existing = await db.execute(select(func.count()).select_from(User))
    return (existing.scalar_one() or 0) == 0


def _banned_redirect(user: User) -> RedirectResponse:
    """Bounce a banned user to login with their reason attached."""

    settings = get_settings()
    base = f"{settings.frontend_origin.rstrip('/')}/#/login?error=banned"
    reason = (user.ban_reason or "").strip()
    if reason:
        # Encode the reason as a query arg so the login page can surface it
        # verbatim. Reason is capped at 500 chars by the DB column so we don't
        # need to trim it further here.
        from urllib.parse import quote

        base = f"{base}&reason={quote(reason)}"
    redirect = RedirectResponse(url=base, status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie(STATE_COOKIE, path="/")
    redirect.delete_cookie(SESSION_COOKIE, path="/")
    return redirect


def _session_redirect() -> RedirectResponse:
    settings = get_settings()
    redirect = RedirectResponse(url=f"{settings.frontend_origin.rstrip('/')}/#/")
    redirect.delete_cookie(STATE_COOKIE, path="/")
    return redirect


def _attach_session_cookie(redirect: RedirectResponse, session_token: str) -> None:
    settings = get_settings()
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=_SESSION_COOKIE_MAX_AGE_S,
        path="/",
    )


@router.post("/dev/login", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
@limiter.limit("30/minute", key_func=user_key)
async def dev_login(
    request: Request,
    body: DevLoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    settings = get_settings()
    if not settings.enable_dev_auth:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    username = body.username.strip()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        is_first = await _is_first_user(db)
        user = User(
            username=username,
            bio="",
            avatar_url=None,
            is_deleted=False,
            is_superuser=is_first,
            can_create_orgs=is_first,
        )
        db.add(user)
        if is_first:
            await db.flush()
            await audit_service.record(
                db,
                action="admin.bootstrap.superuser",
                actor_user_id=user.id,
                target_type="user",
                target_id=user.id,
                metadata={"reason": "first_user", "provider": "dev"},
            )
        await db.commit()
        await db.refresh(user)
    if user.is_banned:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "banned", "reason": user.ban_reason or ""},
        )
    await org_service.ensure_personal_organization(db, user)
    token, _row = await create_session(db, user.id)
    await audit_service.record(
        db,
        action="auth.login.dev",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip=_client_ip(request),
    )
    await db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=_SESSION_COOKIE_MAX_AGE_S,
        path="/",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
@limiter.limit("60/minute", key_func=user_key)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    exetasi_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    if exetasi_session:
        token_hash = hash_session_token(exetasi_session)
        row = (
            await db.execute(
                select(DbSession).where(DbSession.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        actor_id: uuid.UUID | None = row.user_id if row else None
        await revoke_session(db, token_hash)
        if actor_id is not None:
            await audit_service.record(
                db,
                action="auth.logout",
                actor_user_id=actor_id,
                target_type="user",
                target_id=actor_id,
                ip=_client_ip(request),
            )
            await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/github/start")
@limiter.limit("30/minute")
async def github_start(request: Request) -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured (GITHUB_CLIENT_ID).",
        )
    state = uuid.uuid4().hex
    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/github/callback"
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
    )
    return _oauth_start_redirect(f"https://github.com/login/oauth/authorize?{query}", state)


async def _complete_oauth_login(
    request: Request,
    db: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
    suggested_username: str,
    avatar_url: str | None,
) -> RedirectResponse:
    user = await _find_or_create_oauth_user(
        db,
        provider=provider,
        provider_user_id=provider_user_id,
        suggested_username=suggested_username,
        avatar_url=avatar_url,
    )
    if user.is_banned:
        return _banned_redirect(user)
    await org_service.ensure_personal_organization(db, user)
    session_token, _row = await create_session(db, user.id)
    await audit_service.record(
        db,
        action=f"auth.login.oauth.{provider}",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        metadata={"provider": provider},
        ip=_client_ip(request),
    )
    await db.commit()
    redirect = _session_redirect()
    _attach_session_cookie(redirect, session_token)
    return redirect


@router.get("/github/callback")
@limiter.limit("30/minute")
async def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    try:
        _validate_oauth_state(request, state)
    except _OAuthStateError:
        return _login_error_redirect("oauth_state")

    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/github/callback"
    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=30.0,
            )
            token_res.raise_for_status()
            access_token = token_res.json().get("access_token")
            if not access_token:
                return _login_error_redirect("oauth_provider")
            user_res = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            user_res.raise_for_status()
            gh = user_res.json()
    except httpx.HTTPError:
        return _login_error_redirect("oauth_provider")

    gh_id = str(gh["id"])
    login = str(gh.get("login") or f"github_{gh_id}")
    avatar = str(gh["avatar_url"]) if gh.get("avatar_url") else None

    return await _complete_oauth_login(
        request,
        db,
        provider="github",
        provider_user_id=gh_id,
        suggested_username=login,
        avatar_url=avatar,
    )


@router.get("/google/start")
@limiter.limit("30/minute")
async def google_start(request: Request) -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured (GOOGLE_CLIENT_ID).",
        )
    state = uuid.uuid4().hex
    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/google/callback"
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
        }
    )
    return _oauth_start_redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{query}", state)


@router.get("/google/callback")
@limiter.limit("30/minute")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    try:
        _validate_oauth_state(request, state)
    except _OAuthStateError:
        return _login_error_redirect("oauth_state")

    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/google/callback"
    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            token_res.raise_for_status()
            token_body = token_res.json()
            access_token = token_body.get("access_token")
            if not access_token:
                return _login_error_redirect("oauth_provider")
            user_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            user_res.raise_for_status()
            info = user_res.json()
    except httpx.HTTPError:
        return _login_error_redirect("oauth_provider")

    sub = str(info.get("sub") or "")
    if not sub:
        return _login_error_redirect("oauth_provider")
    email = str(info.get("email") or "")
    local = email.split("@", 1)[0] if email and "@" in email else ""
    suggested = local or str(info.get("name") or "").replace(" ", "_") or f"google_{sub[:16]}"
    avatar = str(info["picture"]) if info.get("picture") else None

    return await _complete_oauth_login(
        request,
        db,
        provider="google",
        provider_user_id=sub,
        suggested_username=suggested,
        avatar_url=avatar,
    )


@router.get("/gitlab/start")
@limiter.limit("30/minute")
async def gitlab_start(request: Request) -> RedirectResponse:
    settings = get_settings()
    if not settings.gitlab_client_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitLab OAuth is not configured (GITLAB_CLIENT_ID).",
        )
    state = uuid.uuid4().hex
    base = settings.gitlab_oauth_base_url.rstrip("/")
    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/gitlab/callback"
    query = urlencode(
        {
            "client_id": settings.gitlab_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "read_user",
        }
    )
    return _oauth_start_redirect(f"{base}/oauth/authorize?{query}", state)


@router.get("/gitlab/callback")
@limiter.limit("30/minute")
async def gitlab_callback(
    request: Request,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    try:
        _validate_oauth_state(request, state)
    except _OAuthStateError:
        return _login_error_redirect("oauth_state")

    base = settings.gitlab_oauth_base_url.rstrip("/")
    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/gitlab/callback"
    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                f"{base}/oauth/token",
                data={
                    "client_id": settings.gitlab_client_id,
                    "client_secret": settings.gitlab_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            token_res.raise_for_status()
            token_body = token_res.json()
            access_token = token_body.get("access_token")
            if not access_token:
                return _login_error_redirect("oauth_provider")
            user_res = await client.get(
                f"{base}/api/v4/user",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            user_res.raise_for_status()
            gl = user_res.json()
    except httpx.HTTPError:
        return _login_error_redirect("oauth_provider")

    gl_id = str(gl.get("id") or "")
    if not gl_id:
        return _login_error_redirect("oauth_provider")
    username = str(gl.get("username") or f"gitlab_{gl_id}")
    avatar = str(gl["avatar_url"]) if gl.get("avatar_url") else None

    return await _complete_oauth_login(
        request,
        db,
        provider="gitlab",
        provider_user_id=gl_id,
        suggested_username=username,
        avatar_url=avatar,
    )
