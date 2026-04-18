from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemAnnouncement(Base, TimestampMixin):
    """Platform-wide alert shown on login.

    Multiple rows can coexist (the UI stacks them in reverse-chronological
    order); ``starts_at`` / ``ends_at`` bound the active window so we don't
    need a separate "archive" flow — an announcement just ages out.
    """

    __tablename__ = "system_announcements"
    __table_args__ = (
        Index(
            "ix_system_announcements_active",
            "ends_at",
            "starts_at",
        ),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # `info` / `warning` / `critical`. Stored as a string so migrations can
    # add a level without rewriting rows.
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    # Both ends nullable so a super-user can create an "open-ended" alert
    # (e.g. an active incident with no known resolution time).
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class OrgAlert(Base, TimestampMixin):
    """Per-organization alert shown when a user first enters the org page."""

    __tablename__ = "org_alerts"
    __table_args__ = (
        Index("ix_org_alerts_org_active", "org_id", "ends_at", "starts_at"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class AlertAcknowledgement(Base, TimestampMixin):
    """Per-user dismissal record for a system or org alert.

    ``alert_kind`` + ``alert_id`` form a polymorphic reference — ``alert_id``
    points at ``system_announcements.id`` when ``alert_kind='system'`` and
    at ``org_alerts.id`` when ``alert_kind='org'``. A dedicated FK per kind
    would be cleaner but would also require twice the indexes; the
    polymorphic shape is explicitly documented here to avoid surprises.
    """

    __tablename__ = "alert_acknowledgements"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "alert_kind", "alert_id", name="uq_alert_ack_user_alert"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    alert_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
