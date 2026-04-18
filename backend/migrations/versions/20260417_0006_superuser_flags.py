"""Super-user, ban, and org-creation gating flags on users."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260417_0006"
down_revision = "20260417_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_banned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("ban_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "can_create_orgs",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "can_create_orgs")
    op.drop_column("users", "ban_reason")
    op.drop_column("users", "is_banned")
    op.drop_column("users", "is_superuser")
