"""Organization theming: banner and brand colors."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260417_0004"
down_revision = "20260412_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("banner_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("primary_color", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("secondary_color", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("accent_color", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "accent_color")
    op.drop_column("organizations", "secondary_color")
    op.drop_column("organizations", "primary_color")
    op.drop_column("organizations", "banner_url")
