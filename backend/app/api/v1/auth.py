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
from app.core.security import hash_session_token
from app.models.user import OAuthAccount, User
from app.schemas.auth import DevLoginRequest
from app.services import org_service
from app.services.session_service import create_session, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])

_STATE_MAX_AGE_S = 600


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="oauth-state")


def _validate_oauth_state(request: Request, state: str) -> None:
    raw_state = request.cookies.get(STATE_COOKIE)
    if raw_state is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing OAuth state cookie")
    try:
        expected = _state_serializer().loads(raw_state, max_age=_STATE_MAX_AGE_S)
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state") from exc
    if expected != state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="OAuth state mismatch")


def _oauth_start_redirect(authorize_url: str, state: str) -> RedirectResponse:
    redirect = RedirectResponse(url=authorize_url)
    redirect.set_cookie(
        key=STATE_COOKIE,
        value=_state_serializer().dumps(state),
        httponly=True,
        samesite="lax",
        secure=False,
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

    raw = suggested_username.strip() or f"{provider}_{provider_user_id}"
    base = raw[:64]
    candidate = base
    suffix = 0
    while True:
        exists = await db.execute(select(User.id).where(User.username == candidate))
        if exists.scalar_one_or_none() is None:
            break
        suffix += 1
        candidate = f"{base[:50]}_{suffix}"[:64]

    user = User(
        username=candidate,
        bio="",
        avatar_url=avatar_url,
        is_deleted=False,
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
    await db.commit()
    await db.refresh(user)
    return user


def _session_redirect() -> RedirectResponse:
    settings = get_settings()
    redirect = RedirectResponse(url=f"{settings.frontend_origin.rstrip('/')}/#/")
    redirect.delete_cookie(STATE_COOKIE, path="/")
    return redirect


def _attach_session_cookie(redirect: RedirectResponse, session_token: str) -> None:
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


@router.post("/dev/login", status_code=status.HTTP_204_NO_CONTENT)
async def dev_login(
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
        user = User(username=username, bio="", avatar_url=None, is_deleted=False)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    await org_service.ensure_personal_organization(db, user)
    token, _row = await create_session(db, user.id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    exetasi_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    if exetasi_session:
        await revoke_session(db, hash_session_token(exetasi_session))
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/github/start")
async def github_start() -> RedirectResponse:
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


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    _validate_oauth_state(request, state)
    redirect = _session_redirect()

    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/github/callback"
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
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="GitHub token exchange failed")
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=30.0,
        )
        user_res.raise_for_status()
        gh = user_res.json()

    gh_id = str(gh["id"])
    login = str(gh.get("login") or f"github_{gh_id}")
    avatar = str(gh["avatar_url"]) if gh.get("avatar_url") else None

    user = await _find_or_create_oauth_user(
        db,
        provider="github",
        provider_user_id=gh_id,
        suggested_username=login,
        avatar_url=avatar,
    )
    await org_service.ensure_personal_organization(db, user)
    session_token, _row = await create_session(db, user.id)
    _attach_session_cookie(redirect, session_token)
    return redirect


@router.get("/google/start")
async def google_start() -> RedirectResponse:
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
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    _validate_oauth_state(request, state)
    redirect = _session_redirect()

    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/google/callback"
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
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Google token exchange failed")
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        user_res.raise_for_status()
        info = user_res.json()

    sub = str(info.get("sub") or "")
    if not sub:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Google userinfo missing sub")
    email = str(info.get("email") or "")
    local = email.split("@", 1)[0] if email and "@" in email else ""
    suggested = local or str(info.get("name") or "").replace(" ", "_") or f"google_{sub[:16]}"
    avatar = str(info["picture"]) if info.get("picture") else None

    user = await _find_or_create_oauth_user(
        db,
        provider="google",
        provider_user_id=sub,
        suggested_username=suggested,
        avatar_url=avatar,
    )
    await org_service.ensure_personal_organization(db, user)
    session_token, _row = await create_session(db, user.id)
    _attach_session_cookie(redirect, session_token)
    return redirect


@router.get("/gitlab/start")
async def gitlab_start() -> RedirectResponse:
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
async def gitlab_callback(
    request: Request,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    _validate_oauth_state(request, state)
    redirect = _session_redirect()
    base = settings.gitlab_oauth_base_url.rstrip("/")
    redirect_uri = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/gitlab/callback"

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
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="GitLab token exchange failed")
        user_res = await client.get(
            f"{base}/api/v4/user",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        user_res.raise_for_status()
        gl = user_res.json()

    gl_id = str(gl.get("id") or "")
    if not gl_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="GitLab user missing id")
    username = str(gl.get("username") or f"gitlab_{gl_id}")
    avatar = str(gl["avatar_url"]) if gl.get("avatar_url") else None

    user = await _find_or_create_oauth_user(
        db,
        provider="gitlab",
        provider_user_id=gl_id,
        suggested_username=username,
        avatar_url=avatar,
    )
    await org_service.ensure_personal_organization(db, user)
    session_token, _row = await create_session(db, user.id)
    _attach_session_cookie(redirect, session_token)
    return redirect
