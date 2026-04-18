"""Direct messaging between users + fan-out to org owners and super-users."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260417_0007"
down_revision = "20260417_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "sender_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recipient_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_kind", sa.String(length=16), nullable=False),
        sa.Column(
            "target_org_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_messages_recipient_created",
        "messages",
        ["recipient_id", "created_at"],
    )
    op.create_index(
        "ix_messages_sender_created",
        "messages",
        ["sender_id", "created_at"],
    )
    op.create_index(
        "ix_messages_recipient_read",
        "messages",
        ["recipient_id", "read_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_recipient_read", table_name="messages")
    op.drop_index("ix_messages_sender_created", table_name="messages")
    op.drop_index("ix_messages_recipient_created", table_name="messages")
    op.drop_table("messages")
