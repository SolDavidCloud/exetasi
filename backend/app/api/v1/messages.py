"""User-to-user messaging routes.

Rate-limit budget mirrors the auth endpoints: a tight per-IP bucket
(catches scripted enumeration) stacked with a slightly larger per-user
bucket (catches a single logged-in account hammering recipients). The
daily cap is enforced per-user only.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.ratelimit import limiter, user_key
from app.models.user import User
from app.schemas.message import (
    MessageInbox,
    MessagePublic,
    SendResult,
    SendToOrgOwnersRequest,
    SendToSuperusersRequest,
    SendToUserRequest,
)
from app.services import message_service
from app.services.message_service import UnknownRecipientError

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=MessageInbox)
@limiter.limit("60/minute")
@limiter.limit("120/minute", key_func=user_key)
async def list_inbox(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    unread: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MessageInbox:
    rows = await message_service.list_inbox(
        db, user=current, limit=limit, offset=offset, unread_only=unread
    )
    items = await message_service.hydrate_messages(db, rows)
    unread_count = await message_service.count_unread(db, user=current)
    return MessageInbox(
        items=[MessagePublic(**i) for i in items],
        unread=unread_count,
    )


@router.get("/sent", response_model=list[MessagePublic])
@limiter.limit("60/minute")
@limiter.limit("120/minute", key_func=user_key)
async def list_sent(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MessagePublic]:
    rows = await message_service.list_sent(db, user=current, limit=limit, offset=offset)
    items = await message_service.hydrate_messages(db, rows)
    return [MessagePublic(**i) for i in items]


@router.post(
    "/to-user",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
)
# Send caps intentionally mirror auth endpoints (tight IP + user + daily).
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
@limiter.limit("200/day", key_func=user_key)
async def send_to_user(
    request: Request,
    body: SendToUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> MessagePublic:
    try:
        row = await message_service.send_to_user(
            db,
            sender=current,
            recipient_username=body.recipient_username,
            body=body.body,
        )
    except UnknownRecipientError as exc:
        # Shape the response identically to any other 404 so a probing
        # client cannot distinguish "no such user" from "banned user" from
        # "user exists but messaging disabled".
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Recipient not found"
        ) from exc
    await db.commit()
    await db.refresh(row)
    [hydrated] = await message_service.hydrate_messages(db, [row])
    return MessagePublic(**hydrated)


@router.post(
    "/to-org/{org_slug}",
    response_model=SendResult,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
@limiter.limit("100/day", key_func=user_key)
async def send_to_org_owners(
    request: Request,
    org_slug: str,
    body: SendToOrgOwnersRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> SendResult:
    count = await message_service.send_to_org_owners(
        db, sender=current, org_slug=org_slug, body=body.body
    )
    await db.commit()
    return SendResult(recipients=count)


@router.post(
    "/to-superusers",
    response_model=SendResult,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
@limiter.limit("10/minute", key_func=user_key)
@limiter.limit("50/day", key_func=user_key)
async def send_to_superusers(
    request: Request,
    body: SendToSuperusersRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> SendResult:
    count = await message_service.send_to_superusers(db, sender=current, body=body.body)
    await db.commit()
    return SendResult(recipients=count)


@router.post("/{message_id}/read", response_model=MessagePublic)
@limiter.limit("120/minute")
@limiter.limit("240/minute", key_func=user_key)
async def mark_read(
    request: Request,
    message_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> MessagePublic:
    row = await message_service.mark_read(db, user=current, message_id=message_id)
    await db.commit()
    await db.refresh(row)
    [hydrated] = await message_service.hydrate_messages(db, [row])
    return MessagePublic(**hydrated)


@router.post("/read-all", response_model=SendResult)
@limiter.limit("20/minute")
@limiter.limit("40/minute", key_func=user_key)
async def mark_all_read(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> SendResult:
    count = await message_service.mark_all_read(db, user=current)
    await db.commit()
    return SendResult(recipients=count)
