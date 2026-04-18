"""System announcements + org alerts + per-user dismissal tracking.

Like the other services, mutations flush rows into the caller's session
but never commit — the route is responsible for the final commit so any
audit row lives in the same transaction.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertAcknowledgement, OrgAlert, SystemAnnouncement
from app.models.organization import Membership, Organization
from app.models.user import User

SYSTEM_KIND = "system"
ORG_KIND = "org"


async def create_system_announcement(
    db: AsyncSession,
    *,
    actor: User,
    title: str,
    body: str,
    severity: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
    dismissible: bool,
) -> SystemAnnouncement:
    row = SystemAnnouncement(
        title=title,
        body=body,
        severity=severity,
        starts_at=starts_at,
        ends_at=ends_at,
        dismissible=dismissible,
        created_by_user_id=actor.id,
    )
    db.add(row)
    await db.flush()
    return row


async def delete_system_announcement(
    db: AsyncSession, *, announcement_id: uuid.UUID
) -> None:
    row = await db.get(SystemAnnouncement, announcement_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    await db.delete(row)


async def list_active_system_announcements(
    db: AsyncSession, *, user: User
) -> list[SystemAnnouncement]:
    """Announcements in-window for *user* that they haven't dismissed yet."""

    now = datetime.now(UTC)
    acked = await _acked_ids(db, user=user, kind=SYSTEM_KIND)
    stmt = (
        select(SystemAnnouncement)
        .where(
            or_(
                SystemAnnouncement.starts_at.is_(None),
                SystemAnnouncement.starts_at <= now,
            ),
            or_(
                SystemAnnouncement.ends_at.is_(None),
                SystemAnnouncement.ends_at >= now,
            ),
        )
        .order_by(SystemAnnouncement.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    return [r for r in rows if r.id not in acked]


async def list_all_system_announcements(db: AsyncSession) -> list[SystemAnnouncement]:
    """Super-user view: include past/future rows as well."""

    stmt = select(SystemAnnouncement).order_by(SystemAnnouncement.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_org_alert(
    db: AsyncSession,
    *,
    actor: User,
    org: Organization,
    title: str,
    body: str,
    severity: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
    dismissible: bool,
) -> OrgAlert:
    row = OrgAlert(
        org_id=org.id,
        title=title,
        body=body,
        severity=severity,
        starts_at=starts_at,
        ends_at=ends_at,
        dismissible=dismissible,
        created_by_user_id=actor.id,
    )
    db.add(row)
    await db.flush()
    return row


async def delete_org_alert(
    db: AsyncSession, *, org: Organization, alert_id: uuid.UUID
) -> None:
    row = await db.get(OrgAlert, alert_id)
    # Guard against cross-org id probing: the caller already passes the
    # org context so we can refuse a mismatch outright.
    if row is None or row.org_id != org.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    await db.delete(row)


async def list_active_org_alerts(
    db: AsyncSession, *, user: User, org: Organization
) -> list[OrgAlert]:
    now = datetime.now(UTC)
    acked = await _acked_ids(db, user=user, kind=ORG_KIND)
    stmt = (
        select(OrgAlert)
        .where(
            OrgAlert.org_id == org.id,
            or_(OrgAlert.starts_at.is_(None), OrgAlert.starts_at <= now),
            or_(OrgAlert.ends_at.is_(None), OrgAlert.ends_at >= now),
        )
        .order_by(OrgAlert.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    return [r for r in rows if r.id not in acked]


async def list_all_org_alerts(
    db: AsyncSession, *, org: Organization
) -> list[OrgAlert]:
    stmt = (
        select(OrgAlert)
        .where(OrgAlert.org_id == org.id)
        .order_by(OrgAlert.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge(
    db: AsyncSession, *, user: User, kind: str, alert_id: uuid.UUID
) -> None:
    """Record a user's dismissal of an alert.

    Idempotent: a second ack from the same user collapses into a no-op
    instead of raising a unique-constraint error. This keeps the "don't
    show me again" button safe against double-click / replay.
    """

    existing = await db.execute(
        select(AlertAcknowledgement).where(
            AlertAcknowledgement.user_id == user.id,
            AlertAcknowledgement.alert_kind == kind,
            AlertAcknowledgement.alert_id == alert_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return

    row = AlertAcknowledgement(
        user_id=user.id,
        alert_kind=kind,
        alert_id=alert_id,
    )
    db.add(row)
    await db.flush()


async def ensure_org_owner_or_superuser(
    db: AsyncSession, *, user: User, org: Organization
) -> None:
    """Authorization gate used by the org-alert CRUD routes."""

    if user.is_superuser:
        return
    res = await db.execute(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user.id,
            Membership.role == "owner",
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only owners can manage alerts."
        )


async def _acked_ids(
    db: AsyncSession, *, user: User, kind: str
) -> set[uuid.UUID]:
    res = await db.execute(
        select(AlertAcknowledgement.alert_id).where(
            AlertAcknowledgement.user_id == user.id,
            AlertAcknowledgement.alert_kind == kind,
        )
    )
    return {row[0] for row in res.all()}


__all__ = [
    "ORG_KIND",
    "SYSTEM_KIND",
    "acknowledge",
    "create_org_alert",
    "create_system_announcement",
    "delete_org_alert",
    "delete_system_announcement",
    "ensure_org_owner_or_superuser",
    "list_active_org_alerts",
    "list_active_system_announcements",
    "list_all_org_alerts",
    "list_all_system_announcements",
]
