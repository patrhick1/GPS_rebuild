"""add deleted_at to assessments for soft delete

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-06-16 15:00:00.000000

Enables the "Delete Assessments" feature Sherri asked for on
2026-06-16. Soft delete chosen over hard delete so the row + results
stay around for audit / admin export / accidental-recovery purposes;
user-facing GETs filter on deleted_at IS NULL.

`status` is already overloaded ("in_progress", "completed", "abandoned"),
so a separate nullable timestamp column is cleaner than adding a
"deleted" status value.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    # Partial index — only non-deleted rows are hit by the user-facing
    # filters, so we don't bloat the index with deleted rows.
    op.create_index(
        "ix_assessments_user_id_active",
        "assessments",
        ["user_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_assessments_user_id_active", table_name="assessments")
    op.drop_column("assessments", "deleted_at")
