from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.ratelimit import limiter, user_key
from app.models.organization import Membership, Organization
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationPublic,
    OrganizationUpdate,
)
from app.services import audit_service, org_service
from app.utils.ip import client_ip
from app.utils.slug import slugify

router = APIRouter(prefix="/orgs", tags=["organizations"])


def _to_public(org: Organization, role: str) -> OrganizationPublic:
    """Build the wire response with the caller's role attached."""

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
        role=role,  # type: ignore[arg-type]
    )


async def _membership_for(
    db: AsyncSession, user_id: uuid.UUID, org_slug: str
) -> tuple[Organization, Membership]:
    """Return (org, membership) if the user is a member of the org, else 404.

    Uses 404 (not 403) when the caller is not a member so non-members cannot
    enumerate existing organizations.
    """

    result = await db.execute(
        select(Organization, Membership)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Organization.slug == org_slug, Membership.user_id == user_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    org, membership = row
    return org, membership


@router.get("", response_model=list[OrganizationPublic])
async def list_orgs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[OrganizationPublic]:
    rows = await org_service.list_organizations_for_user(db, current.id)
    return [_to_public(org, role) for org, role in rows]


@router.post("", response_model=OrganizationPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
async def create_org(
    request: Request,
    body: OrganizationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> OrganizationPublic:
    if not (current.is_superuser or current.can_create_orgs):
        # Platform default is "no-one can create orgs"; super-users grant
        # `can_create_orgs` per-user via the admin panel.
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Organization creation requires approval from an administrator.",
        )
    slug = body.slug.strip() if body.slug else slugify(body.name)
    taken = await db.execute(select(Organization.id).where(Organization.slug == slug))
    if taken.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug already in use")
    org = Organization(
        name=body.name.strip(),
        slug=slug,
        description=body.description.strip(),
        avatar_url=None,
        is_personal=False,
        owner_user_id=current.id,
    )
    db.add(org)
    await db.flush()
    db.add(Membership(user_id=current.id, org_id=org.id, role="owner"))
    await audit_service.record(
        db,
        action="org.created",
        actor_user_id=current.id,
        org_id=org.id,
        target_type="organization",
        target_id=org.id,
        metadata={"name": org.name, "slug": org.slug},
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(org)
    return _to_public(org, "owner")


@router.get("/{org_slug}", response_model=OrganizationPublic)
async def get_org(
    org_slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> OrganizationPublic:
    org, membership = await _membership_for(db, current.id, org_slug)
    return _to_public(org, membership.role)


@router.patch("/{org_slug}", response_model=OrganizationPublic)
@limiter.limit("30/minute")
@limiter.limit("60/minute", key_func=user_key)
async def update_org(
    request: Request,
    org_slug: str,
    body: OrganizationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> OrganizationPublic:
    org, membership = await _membership_for(db, current.id, org_slug)
    if membership.role != "owner":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only organization owners can edit settings"
        )

    changed: list[str] = []

    if body.slug is not None and body.slug != org.slug:
        if org.is_personal:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Personal organization slug is derived from the username",
            )
        new_slug = slugify(body.slug)
        taken = await db.execute(
            select(Organization.id).where(
                Organization.slug == new_slug, Organization.id != org.id
            )
        )
        if taken.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug already in use")
        org.slug = new_slug
        changed.append("slug")

    if body.name is not None and body.name.strip() != org.name:
        org.name = body.name.strip()
        changed.append("name")
    if body.description is not None and body.description.strip() != org.description:
        org.description = body.description.strip()
        changed.append("description")
    if body.avatar_url is not None:
        org.avatar_url = body.avatar_url.strip() or None
        changed.append("avatar_url")
    if body.banner_url is not None:
        org.banner_url = body.banner_url.strip() or None
        changed.append("banner_url")
    if body.primary_color is not None:
        org.primary_color = body.primary_color or None
        changed.append("primary_color")
    if body.secondary_color is not None:
        org.secondary_color = body.secondary_color or None
        changed.append("secondary_color")
    if body.accent_color is not None:
        org.accent_color = body.accent_color or None
        changed.append("accent_color")

    if changed:
        await audit_service.record(
            db,
            action="org.updated",
            actor_user_id=current.id,
            org_id=org.id,
            target_type="organization",
            target_id=org.id,
            metadata={"fields": changed},
            ip=client_ip(request),
        )

    await db.commit()
    await db.refresh(org)
    return _to_public(org, membership.role)
