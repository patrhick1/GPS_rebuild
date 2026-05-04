"""add description_es to gifts_passions

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-05-01 12:00:00.000000

Phase D of the v2.1 addendum: Spanish description for the 19 spiritual gifts
+ 5 influencing styles displayed on the GPS results page when user locale is
'es'. Column is nullable; the frontend falls back to `description` (English)
when the Spanish value isn't populated yet. Content backfill happens in a
separate data migration once Brian's team supplies the 24 strings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'gifts_passions',
        sa.Column('description_es', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('gifts_passions', 'description_es')
