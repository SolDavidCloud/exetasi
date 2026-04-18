"""System announcements + org alerts + user acknowledgements."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260417_0008"
down_revision = "20260417_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_announcements",
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
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.String(length=16),
            nullable=False,
            server_default="info",
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "dismissible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_system_announcements_active",
        "system_announcements",
        ["ends_at", "starts_at"],
    )

    op.create_table(
        "org_alerts",
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
            "org_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.String(length=16),
            nullable=False,
            server_default="info",
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "dismissible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_org_alerts_org_active",
        "org_alerts",
        ["org_id", "ends_at", "starts_at"],
    )

    op.create_table(
        "alert_acknowledgements",
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
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alert_kind", sa.String(length=16), nullable=False),
        sa.Column("alert_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "alert_kind",
            "alert_id",
            name="uq_alert_ack_user_alert",
        ),
    )
    op.create_index(
        "ix_alert_acknowledgements_user_id",
        "alert_acknowledgements",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_alert_acknowledgements_user_id",
        table_name="alert_acknowledgements",
    )
    op.drop_table("alert_acknowledgements")
    op.drop_index("ix_org_alerts_org_active", table_name="org_alerts")
    op.drop_table("org_alerts")
    op.drop_index(
        "ix_system_announcements_active", table_name="system_announcements"
    )
    op.drop_table("system_announcements")
