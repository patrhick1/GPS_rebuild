"""add webhook_events for Stripe idempotency

Revision ID: b5d1f0e2a3c4
Revises: a1b2c3d4e5f6
Create Date: 2026-04-30 12:00:00.000000

Stripe retries webhook delivery on any non-2xx, and occasionally
delivers duplicates anyway. We dedupe by inserting the event id with
ON CONFLICT DO NOTHING and only running the handler if the insert
created a row.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d1f0e2a3c4'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('stripe_event_id', sa.String(255), nullable=False, unique=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column(
            'processed_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
    )
    op.create_index(
        'ix_webhook_events_event_type_processed_at',
        'webhook_events',
        ['event_type', 'processed_at'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_webhook_events_event_type_processed_at',
        table_name='webhook_events',
    )
    op.drop_table('webhook_events')
