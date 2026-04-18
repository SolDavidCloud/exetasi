from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.ratelimit import limiter, user_key
from app.models.exam import Exam, ExamVersion
from app.models.organization import Membership, Organization
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamPublic
from app.services import audit_service
from app.utils.ip import client_ip

router = APIRouter(prefix="/orgs", tags=["exams"])


_EDITOR_ROLES = frozenset({"owner", "editor"})


async def _membership_for(
    db: AsyncSession, user_id: uuid.UUID, org_slug: str
) -> tuple[Organization, Membership]:
    """Return (org, membership) or 404 if the caller is not a member.

    404 (not 403) hides org existence from non-members.
    """

    result = await db.execute(
        select(Organization, Membership)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Organization.slug == org_slug, Membership.user_id == user_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return row


@router.get("/{org_slug}/exams", response_model=list[ExamPublic])
async def list_exams(
    org_slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[Exam]:
    org, _ = await _membership_for(db, current.id, org_slug)
    result = await db.execute(select(Exam).where(Exam.org_id == org.id).order_by(Exam.name))
    return list(result.scalars().all())


@router.post("/{org_slug}/exams", response_model=ExamPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
@limiter.limit("40/minute", key_func=user_key)
async def create_exam(
    request: Request,
    org_slug: str,
    body: ExamCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> Exam:
    org, membership = await _membership_for(db, current.id, org_slug)
    if membership.role not in _EDITOR_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only owners and editors can create exams",
        )
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
    await audit_service.record(
        db,
        action="exam.created",
        actor_user_id=current.id,
        org_id=org.id,
        target_type="exam",
        target_id=exam.id,
        metadata={"name": exam.name, "visibility": exam.visibility},
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(exam)
    return exam
