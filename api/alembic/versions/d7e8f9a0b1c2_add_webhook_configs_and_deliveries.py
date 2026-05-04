"""add webhook_configs and webhook_deliveries

Revision ID: d7e8f9a0b1c2
Revises: c6a7b8d9e0f1
Create Date: 2026-04-30 18:00:00.000000

Phase B of the v2.1 addendum: webhook infrastructure for assessment-completion
and user-registration events. One config per (org, event_type), append-only
deliveries log with retry status.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = 'c6a7b8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'webhook_configs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column(
            'organization_id',
            sa.UUID(),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('webhook_url', sa.String(2048), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('secret', sa.String(255), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.UniqueConstraint(
            'organization_id', 'event_type', name='uq_webhook_configs_org_event'
        ),
    )
    op.create_index(
        'ix_webhook_configs_org_active',
        'webhook_configs',
        ['organization_id', 'is_active'],
    )

    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column(
            'webhook_config_id',
            sa.UUID(),
            sa.ForeignKey('webhook_configs.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('http_status_code', sa.SmallInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempts', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
    )
    op.create_index(
        'ix_webhook_deliveries_status_next_retry',
        'webhook_deliveries',
        ['status', 'next_retry_at'],
    )
    op.create_index(
        'ix_webhook_deliveries_config_created',
        'webhook_deliveries',
        ['webhook_config_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_webhook_deliveries_config_created', table_name='webhook_deliveries'
    )
    op.drop_index(
        'ix_webhook_deliveries_status_next_retry', table_name='webhook_deliveries'
    )
    op.drop_table('webhook_deliveries')

    op.drop_index('ix_webhook_configs_org_active', table_name='webhook_configs')
    op.drop_table('webhook_configs')
