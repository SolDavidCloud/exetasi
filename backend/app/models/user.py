from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

_INACTIVITY = timedelta(days=7)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    bio: Mapped[str] = mapped_column(String(512), default="")
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Platform-level role flags. Governed by `admin_service` (super-user only
    # mutation surface). `is_superuser` grants access to the admin screen and
    # is always allowed to create organizations regardless of
    # `can_create_orgs`. `is_banned` short-circuits login and hides the user's
    # visible content from others; `ban_reason` is shown to the banned user on
    # their next login attempt.
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ban_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    can_create_orgs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OAuthAccount(Base, TimestampMixin):
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_subject"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped[User] = relationship(back_populates="oauth_accounts")


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")

    def touch(self) -> None:
        now = datetime.now(UTC)
        self.last_active_at = now
        self.expires_at = now + _INACTIVITY
