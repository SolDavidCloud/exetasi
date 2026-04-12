from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.exam import Exam, ExamVersion
from app.models.organization import Membership, Organization
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamPublic

router = APIRouter(prefix="/orgs", tags=["exams"])


async def _org_for_member(
    db: AsyncSession, user_id: uuid.UUID, org_slug: str
) -> Organization:
    result = await db.execute(
        select(Organization)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Organization.slug == org_slug, Membership.user_id == user_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.get("/{org_slug}/exams", response_model=list[ExamPublic])
async def list_exams(
    org_slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[Exam]:
    org = await _org_for_member(db, current.id, org_slug)
    result = await db.execute(select(Exam).where(Exam.org_id == org.id).order_by(Exam.name))
    return list(result.scalars().all())


@router.post("/{org_slug}/exams", response_model=ExamPublic, status_code=status.HTTP_201_CREATED)
async def create_exam(
    org_slug: str,
    body: ExamCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> Exam:
    org = await _org_for_member(db, current.id, org_slug)
    exam = Exam(
        org_id=org.id,
        name=body.name.strip(),
        public_description=body.public_description,
        private_description=body.private_description,
        is_archived=False,
        visibility=body.visibility,
        created_by=current.id,
    )
    db.add(exam)
    await db.flush()
    version = ExamVersion(
        exam_id=exam.id,
        name="v1",
        public_description="",
        private_description="",
        is_active=True,
        config_json="{}",
    )
    db.add(version)
    await db.commit()
    await db.refresh(exam)
    return exam
