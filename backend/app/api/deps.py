from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.session_service import get_user_by_id, get_valid_session

SESSION_COOKIE = "exetasi_session"
STATE_COOKIE = "oauth_state"


async def session_cookie(
    exetasi_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str | None:
    return exetasi_session


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(session_cookie)],
) -> User:
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    row = await get_valid_session(db, token)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = await get_user_by_id(db, row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    # Banned users lose access even on an already-established session. The ban
    # is enforced here (not only at login) so an active session cannot outlive
    # a ban decision. `admin_service.ban_user` revokes sessions too, but this
    # belt-and-braces check keeps the system safe if a ban was applied via a
    # direct DB edit or a race.
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account banned")
    return user


async def get_current_superuser(
    current: Annotated[User, Depends(get_current_user)],
) -> User:
    """Authenticated, not banned, AND flagged as platform super-user.

    Intentionally returns 404 (not 403) so non-super-users cannot enumerate
    the existence of the admin surface.
    """

    if not current.is_superuser:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    return current


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(session_cookie)],
) -> User | None:
    if token is None:
        return None
    row = await get_valid_session(db, token)
    if row is None:
        return None
    return await get_user_by_id(db, row.user_id)
