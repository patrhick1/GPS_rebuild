"""add name_es to gifts_passions

Revision ID: b6c7d8e9f0a1
Revises: d4e5f7a8b9c0
Create Date: 2026-06-16 10:00:00.000000

Spanish display name for the 19 spiritual gifts + 5 influencing styles
shown as "bubble" labels on the GPS results page. Without this, the
description text translates but the bubble itself ("Teacher",
"Evangelist", ...) stayed English in Spanish locale.

Column is nullable; the frontend falls back to `name` (English) when
the Spanish value isn't populated. Content backfill is the immediate
follow-up migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "d4e5f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gifts_passions",
        sa.Column("name_es", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gifts_passions", "name_es")
