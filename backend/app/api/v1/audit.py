"""Read-only audit log endpoints."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.ratelimit import limiter, user_key
from app.models.audit import AuditLog
from app.models.organization import Membership, Organization
from app.models.user import User

router = APIRouter(tags=["audit"])


@router.get("/audit-log")
@limiter.limit("30/minute")
@limiter.limit("60/minute", key_func=user_key)
async def read_audit_log(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    org_slug: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    """Return recent audit entries the caller is allowed to see.

    - With no ``org_slug``: the caller's own actions (actor = current user).
    - With ``org_slug``: entries for that organization. Caller must be an
      *owner* of that org — other roles get a 404 to avoid leaking existence.
    """

    if org_slug is None:
        # Self-scoped: show both what the user did and actions taken against
        # their own account (both filtered to the current user id).
        q = (
            select(AuditLog)
            .where(
                or_(
                    AuditLog.actor_user_id == current.id,
                    (AuditLog.target_type == "user") & (AuditLog.target_id == current.id),
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    else:
        # Org-scoped: only owners can read, to prevent lower-privileged
        # members from observing who edited what.
        res = await db.execute(
            select(Organization, Membership)
            .join(Membership, Membership.org_id == Organization.id)
            .where(
                Organization.slug == org_slug,
                Membership.user_id == current.id,
            )
        )
        row = res.first()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
        org, membership = row
        if membership.role != "owner":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
        q = (
            select(AuditLog)
            .where(AuditLog.org_id == org.id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )

    rows = (await db.execute(q)).scalars().all()
    return {"entries": [_serialise(row) for row in rows]}


def _serialise(row: AuditLog) -> dict[str, object]:
    try:
        meta = json.loads(row.metadata_json or "{}")
    except (TypeError, ValueError):
        meta = {}
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat(),
        "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
        "org_id": str(row.org_id) if row.org_id else None,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": str(row.target_id) if row.target_id else None,
        "metadata": meta,
    }
