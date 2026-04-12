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
    return user


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
