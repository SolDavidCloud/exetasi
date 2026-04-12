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
    redirect = RedirectResponse(url=f"https://github.com/login/oauth/authorize?{query}")
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


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    raw_state = request.cookies.get(STATE_COOKIE)
    if raw_state is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing OAuth state cookie")
    try:
        expected = _state_serializer().loads(raw_state, max_age=_STATE_MAX_AGE_S)
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state") from exc
    if expected != state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="OAuth state mismatch")

    redirect = RedirectResponse(url=f"{settings.frontend_origin.rstrip('/')}/#/")
    redirect.delete_cookie(STATE_COOKIE, path="/")

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

    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == "github", OAuthAccount.provider_user_id == gh_id
        )
    )
    link = result.scalar_one_or_none()
    if link:
        user = await db.get(User, link.user_id)
        if user is None or user.is_deleted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing")
    else:
        base = login[:64]
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
            avatar_url=(str(gh.get("avatar_url")) if gh.get("avatar_url") else None),
            is_deleted=False,
        )
        db.add(user)
        await db.flush()
        db.add(
            OAuthAccount(
                user_id=user.id,
                provider="github",
                provider_user_id=gh_id,
            )
        )
        await db.commit()
        await db.refresh(user)

    await org_service.ensure_personal_organization(db, user)

    session_token, _row = await create_session(db, user.id)
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return redirect


@router.get("/google/start")
async def google_start() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth not implemented yet")


@router.get("/gitlab/start")
async def gitlab_start() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="GitLab OAuth not implemented yet")
