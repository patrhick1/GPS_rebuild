"""add zapier_activated_at + zapier_canceled_at to subscriptions

Revision ID: aa920c3e892a
Revises: 6559048b8846
Create Date: 2026-06-21 00:00:00.000000

Idempotency markers for the platform-wide Zapier integration. Trigger 2
(Toolkit Activated) fires only when zapier_activated_at IS NULL and the
subscription transitions to active/trialing. Trigger 3 (Toolkit Canceled)
fires only when zapier_canceled_at IS NULL and the subscription transitions
to canceled/unpaid/incomplete_expired. Both columns are set to NOW() on
successful enqueue so a duplicate Stripe webhook delivery or a Render
restart-retry can't double-fire either webhook.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "aa920c3e892a"
down_revision: Union[str, None] = "6559048b8846"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("zapier_activated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("zapier_canceled_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "zapier_canceled_at")
    op.drop_column("subscriptions", "zapier_activated_at")
