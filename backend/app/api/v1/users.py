from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SESSION_COOKIE, get_current_user, get_db
from app.core.security import hash_session_token
from app.models.user import Session as DbSession
from app.models.user import User
from app.schemas.user import UserPublic, UserUpdate
from app.services.session_service import revoke_session

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_me(current: Annotated[User, Depends(get_current_user)]) -> User:
    return current


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> User:
    if body.username is not None:
        exists = await db.execute(
            select(User.id).where(User.username == body.username, User.id != current.id)
        )
        if exists.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Username already taken")
        current.username = body.username
    if body.bio is not None:
        current.bio = body.bio
    if body.avatar_url is not None:
        current.avatar_url = body.avatar_url
    await db.commit()
    await db.refresh(current)
    return current


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    exetasi_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    current.is_deleted = True
    await db.execute(delete(DbSession).where(DbSession.user_id == current.id))
    await db.commit()
    if exetasi_session:
        await revoke_session(db, hash_session_token(exetasi_session))
    response.delete_cookie(SESSION_COOKIE, path="/")
