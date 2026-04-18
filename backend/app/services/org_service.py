from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Membership, Organization
from app.models.user import User
from app.utils.slug import slugify


async def ensure_personal_organization(db: AsyncSession, user: User) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id, Organization.is_personal.is_(True))
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.slug != slugify(user.username):
            existing.slug = slugify(user.username)
            existing.name = user.username
            await db.commit()
            await db.refresh(existing)
        return existing

    slug = slugify(user.username)
    base = slug
    suffix = 0
    while True:
        taken = await db.execute(select(Organization.id).where(Organization.slug == slug))
        if taken.scalar_one_or_none() is None:
            break
        suffix += 1
        slug = f"{base}-{suffix}"[:96]

    org = Organization(
        name=user.username,
        slug=slug,
        description="",
        avatar_url=None,
        is_personal=True,
        owner_user_id=user.id,
    )
    db.add(org)
    await db.flush()
    db.add(Membership(user_id=user.id, org_id=org.id, role="owner"))
    await db.commit()
    await db.refresh(org)
    return org


async def list_organizations_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Organization, str]]:
    """Return (organization, caller role) tuples, ordered by org name."""

    result = await db.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Membership.user_id == user_id)
        .order_by(Organization.name)
    )
    return [(org, role) for org, role in result.all()]
