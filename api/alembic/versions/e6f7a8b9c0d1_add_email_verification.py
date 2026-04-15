"""add email verification

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email_verified column to users (idempotent)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'email_verified'"
    ))
    if not result.fetchone():
        op.add_column('users', sa.Column('email_verified', sa.String(1), nullable=False, server_default='N'))
        # Mark all existing users as verified so they aren't locked out
        op.execute("UPDATE users SET email_verified = 'Y'")

    # Create email_verification_tokens table (idempotent)
    result = conn.execute(sa.text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name = 'email_verification_tokens'"
    ))
    if not result.fetchone():
        op.create_table(
            'email_verification_tokens',
            sa.Column('id', sa.UUID(), primary_key=True),
            sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('token', sa.Text(), nullable=False, unique=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('used', sa.String(1), nullable=False, server_default='N'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )


def downgrade() -> None:
    op.drop_table('email_verification_tokens')
    op.drop_column('users', 'email_verified')
