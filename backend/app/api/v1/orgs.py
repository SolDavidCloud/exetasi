from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.organization import Membership, Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationPublic
from app.services import org_service
from app.utils.slug import slugify

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.get("", response_model=list[OrganizationPublic])
async def list_orgs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[Organization]:
    return await org_service.list_organizations_for_user(db, current.id)


@router.post("", response_model=OrganizationPublic, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: OrganizationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> Organization:
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
    await db.commit()
    await db.refresh(org)
    return org
