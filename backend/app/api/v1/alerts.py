"""System-wide announcements + per-org alerts.

Split into three path families:

- ``/api/v1/announcements`` — GET is authenticated (any user, returns
  only the active-and-unacknowledged rows for that user); writes are
  super-user only and hidden behind 404 for everyone else.
- ``/api/v1/orgs/{slug}/alerts`` — GET for members, writes for owners
  and super-users.
- ``/api/v1/alerts/{kind}/{id}/ack`` — authenticated user records a
  dismissal. ``kind`` is either ``system`` or ``org``; the row is
  idempotent so replay is safe.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser, get_current_user, get_db
from app.core.ratelimit import limiter, user_key
from app.models.organization import Organization
from app.models.user import User
from app.schemas.alert import (
    OrgAlertCreate,
    OrgAlertPublic,
    SystemAnnouncementCreate,
    SystemAnnouncementPublic,
)
from app.services import alert_service, audit_service
from app.services.alert_service import ORG_KIND, SYSTEM_KIND
from app.utils.ip import client_ip

system_router = APIRouter(prefix="/announcements", tags=["alerts"])
org_alert_router = APIRouter(prefix="/orgs", tags=["alerts"])
ack_router = APIRouter(prefix="/alerts", tags=["alerts"])


@system_router.get("/active", response_model=list[SystemAnnouncementPublic])
@limiter.limit("60/minute")
@limiter.limit("120/minute", key_func=user_key)
async def list_active_announcements(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[SystemAnnouncementPublic]:
    rows = await alert_service.list_active_system_announcements(db, user=current)
    return [SystemAnnouncementPublic.model_validate(r) for r in rows]


@system_router.get("", response_model=list[SystemAnnouncementPublic])
@limiter.limit("30/minute")
@limiter.limit("60/minute", key_func=user_key)
async def list_all_announcements(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(get_current_superuser)],
) -> list[SystemAnnouncementPublic]:
    rows = await alert_service.list_all_system_announcements(db)
    return [SystemAnnouncementPublic.model_validate(r) for r in rows]


@system_router.post(
    "",
    response_model=SystemAnnouncementPublic,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
async def create_announcement(
    request: Request,
    body: SystemAnnouncementCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_superuser)],
) -> SystemAnnouncementPublic:
    row = await alert_service.create_system_announcement(
        db,
        actor=admin,
        title=body.title,
        body=body.body,
        severity=body.severity,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        dismissible=body.dismissible,
    )
    await audit_service.record(
        db,
        action="alerts.system.created",
        actor_user_id=admin.id,
        target_type="system_announcement",
        target_id=row.id,
        metadata={"severity": row.severity, "title": row.title[:120]},
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(row)
    return SystemAnnouncementPublic.model_validate(row)


@system_router.delete(
    "/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT
)
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
async def delete_announcement(
    request: Request,
    announcement_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_superuser)],
) -> None:
    await alert_service.delete_system_announcement(
        db, announcement_id=announcement_id
    )
    await audit_service.record(
        db,
        action="alerts.system.deleted",
        actor_user_id=admin.id,
        target_type="system_announcement",
        target_id=announcement_id,
        ip=client_ip(request),
    )
    await db.commit()


@org_alert_router.get(
    "/{org_slug}/alerts/active", response_model=list[OrgAlertPublic]
)
@limiter.limit("60/minute")
@limiter.limit("120/minute", key_func=user_key)
async def list_active_org_alerts(
    request: Request,
    org_slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[OrgAlertPublic]:
    org = await _load_org(db, org_slug)
    rows = await alert_service.list_active_org_alerts(db, user=current, org=org)
    return [OrgAlertPublic.model_validate(r) for r in rows]


@org_alert_router.get("/{org_slug}/alerts", response_model=list[OrgAlertPublic])
@limiter.limit("30/minute")
@limiter.limit("60/minute", key_func=user_key)
async def list_all_org_alerts(
    request: Request,
    org_slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[OrgAlertPublic]:
    org = await _load_org(db, org_slug)
    await alert_service.ensure_org_owner_or_superuser(db, user=current, org=org)
    rows = await alert_service.list_all_org_alerts(db, org=org)
    return [OrgAlertPublic.model_validate(r) for r in rows]


@org_alert_router.post(
    "/{org_slug}/alerts",
    response_model=OrgAlertPublic,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
async def create_org_alert(
    request: Request,
    org_slug: str,
    body: OrgAlertCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> OrgAlertPublic:
    org = await _load_org(db, org_slug)
    await alert_service.ensure_org_owner_or_superuser(db, user=current, org=org)
    row = await alert_service.create_org_alert(
        db,
        actor=current,
        org=org,
        title=body.title,
        body=body.body,
        severity=body.severity,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        dismissible=body.dismissible,
    )
    await audit_service.record(
        db,
        action="alerts.org.created",
        actor_user_id=current.id,
        org_id=org.id,
        target_type="org_alert",
        target_id=row.id,
        metadata={"severity": row.severity, "title": row.title[:120]},
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(row)
    return OrgAlertPublic.model_validate(row)


@org_alert_router.delete(
    "/{org_slug}/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT
)
@limiter.limit("10/minute")
@limiter.limit("20/minute", key_func=user_key)
async def delete_org_alert(
    request: Request,
    org_slug: str,
    alert_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> None:
    org = await _load_org(db, org_slug)
    await alert_service.ensure_org_owner_or_superuser(db, user=current, org=org)
    await alert_service.delete_org_alert(db, org=org, alert_id=alert_id)
    await audit_service.record(
        db,
        action="alerts.org.deleted",
        actor_user_id=current.id,
        org_id=org.id,
        target_type="org_alert",
        target_id=alert_id,
        ip=client_ip(request),
    )
    await db.commit()


@ack_router.post(
    "/{kind}/{alert_id}/ack", status_code=status.HTTP_204_NO_CONTENT
)
@limiter.limit("120/minute")
@limiter.limit("240/minute", key_func=user_key)
async def acknowledge_alert(
    request: Request,
    kind: Literal["system", "org"],
    alert_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> None:
    normalised = SYSTEM_KIND if kind == "system" else ORG_KIND
    await alert_service.acknowledge(
        db, user=current, kind=normalised, alert_id=alert_id
    )
    await db.commit()


async def _load_org(db: AsyncSession, slug: str) -> Organization:
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org
