from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.ip import client_ip as _client_ip

from app.api.deps import SESSION_COOKIE, get_current_user, get_db
from app.core.ratelimit import limiter, user_key
from app.core.security import hash_session_token
from app.models.user import Session as DbSession
from app.models.user import User
from app.schemas.user import UserPublic, UserUpdate
from app.services import audit_service, org_service
from app.services.session_service import revoke_session

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_me(current: Annotated[User, Depends(get_current_user)]) -> User:
    return current


@router.patch("/me", response_model=UserPublic)
@limiter.limit("20/minute")
@limiter.limit("30/minute", key_func=user_key)
async def update_me(
    request: Request,
    body: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> User:
    changed: dict[str, object] = {}
    username_changed = False
    if body.username is not None and body.username != current.username:
        exists = await db.execute(
            select(User.id).where(User.username == body.username, User.id != current.id)
        )
        if exists.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Username already taken")
        changed["username"] = {"from": current.username, "to": body.username}
        current.username = body.username
        username_changed = True
    if body.bio is not None and body.bio != current.bio:
        changed["bio"] = True
    if body.bio is not None:
        current.bio = body.bio
    if body.avatar_url is not None and body.avatar_url != current.avatar_url:
        changed["avatar_url"] = True
    if body.avatar_url is not None:
        current.avatar_url = body.avatar_url
    await db.commit()
    await db.refresh(current)
    # Resync the personal organization slug when the username changed —
    # otherwise share links to /#/orgs/<old-slug> keep pointing at the
    # user until their next login rebuilds the slug.
    if username_changed:
        await org_service.ensure_personal_organization(db, current)
    if changed:
        await audit_service.record(
            db,
            action="user.updated",
            actor_user_id=current.id,
            target_type="user",
            target_id=current.id,
            metadata={"changes": list(changed.keys())},
            ip=_client_ip(request),
        )
        await db.commit()
    return current


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
@limiter.limit("5/minute", key_func=user_key)
async def delete_me(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    exetasi_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    current.is_deleted = True
    await db.execute(delete(DbSession).where(DbSession.user_id == current.id))
    await audit_service.record(
        db,
        action="user.deleted",
        actor_user_id=current.id,
        target_type="user",
        target_id=current.id,
        ip=_client_ip(request),
    )
    await db.commit()
    if exetasi_session:
        await revoke_session(db, hash_session_token(exetasi_session))
    response.delete_cookie(SESSION_COOKIE, path="/")
