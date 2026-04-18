from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """Flat user-to-user message.

    `sender_id` is nullable so soft-deleted senders don't strand their
    messages. `target_kind` records the original send path so the UI can
    render badges like "to all owners of <org>" / "to super-users" even
    though each row is addressed to a single recipient after fan-out.
    """

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_recipient_created", "recipient_id", "created_at"),
        Index("ix_messages_sender_created", "sender_id", "created_at"),
        Index("ix_messages_recipient_read", "recipient_id", "read_at"),
    )

    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # One of "direct" | "org_owners" | "superusers". Stored as a string
    # rather than an enum so migrations can add a kind without rewriting the
    # existing rows.
    target_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Present when `target_kind == "org_owners"` so the UI can show
    # "sent to owners of <org.name>" on both sides of the conversation.
    target_org_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    # UTF-8 text, 500-char max enforced at the schema layer; stored as TEXT
    # to avoid losing multibyte characters on exotic DBs.
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
