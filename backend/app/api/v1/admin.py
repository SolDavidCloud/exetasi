from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser, get_db
from app.core.ratelimit import limiter, user_key
from app.models.user import User
from app.schemas.admin import (
    AdminUserPublic,
    BanUserRequest,
    SetCanCreateOrgsRequest,
    SetSuperuserRequest,
    TransferOwnerRequest,
)
from app.schemas.organization import OrganizationPublic
from app.services import admin_service
from app.utils.ip import client_ip

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserPublic])
@limiter.limit("60/minute")
@limiter.limit("120/minute", key_func=user_key)
async def list_users(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(get_current_superuser)],
    q: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[User]:
    return await admin_service.list_users(db, query=q, limit=limit, offset=offset)


@router.patch("/users/{username}/superuser", response_model=AdminUserPublic)
@limiter.limit("20/minute")
@limiter.limit("60/minute", key_func=user_key)
async def set_superuser(
    request: Request,
    username: str,
    body: SetSuperuserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_superuser)],
) -> User:
    target = await admin_service.set_superuser(
        db,
        actor=admin,
        target_username=username,
        is_superuser=body.is_superuser,
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.patch("/users/{username}/can-create-orgs", response_model=AdminUserPublic)
@limiter.limit("20/minute")
@limiter.limit("60/minute", key_func=user_key)
async def set_can_create_orgs(
    request: Request,
    username: str,
    body: SetCanCreateOrgsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_superuser)],
) -> User:
    target = await admin_service.set_can_create_orgs(
        db,
        actor=admin,
        target_username=username,
        allowed=body.allowed,
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.post("/users/{username}/ban", response_model=AdminUserPublic)
@limiter.limit("10/minute")
@limiter.limit("30/minute", key_func=user_key)
async def ban_user(
    request: Request,
    username: str,
    body: BanUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_superuser)],
) -> User:
    target = await admin_service.ban_user(
        db,
        actor=admin,
        target_username=username,
        reason=body.reason,
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.post("/users/{username}/unban", response_model=AdminUserPublic)
@limiter.limit("10/minute")
@limiter.limit("30/minute", key_func=user_key)
async def unban_user(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_superuser)],
) -> User:
    target = await admin_service.unban_user(
        db,
        actor=admin,
        target_username=username,
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.post(
    "/orgs/{org_slug}/transfer-owner",
    response_model=OrganizationPublic,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
async def transfer_owner(
    request: Request,
    org_slug: str,
    body: TransferOwnerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_superuser)],
) -> OrganizationPublic:
    org = await admin_service.transfer_org_ownership(
        db,
        actor=admin,
        org_slug=org_slug,
        new_owner_username=body.new_owner_username,
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(org)
    return OrganizationPublic(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        avatar_url=org.avatar_url,
        banner_url=org.banner_url,
        primary_color=org.primary_color,
        secondary_color=org.secondary_color,
        accent_color=org.accent_color,
        is_personal=org.is_personal,
        role="owner",
    )
