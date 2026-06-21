"""apply Sherri's authoritative translation for Encouragement

Revision ID: 6d097c824704
Revises: d8e9f0a1b2c3
Create Date: 2026-06-21 00:00:00.000000

Sherri Reishus delivered her approved Spanish translations on 2026-06-21.
Of the 24 entries (19 Spiritual Gifts + 5 Influencing Styles), 23 match
the prior backfill in [c7d8e9f0a1b2](c7d8e9f0a1b2_populate_gifts_passion_name_es.py).
The one delta is Encouragement: "Aliento" (mine) → "Exhortación" (hers,
the traditional Christian-Spanish rendering used for Romans 12:8).

Guards on current value (`name_es = 'Aliento'`) so a hand-edit to
something else won't be clobbered.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "6d097c824704"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        UPDATE gifts_passions
           SET name_es = %s
         WHERE name = %s
           AND name_es = %s
           AND type_id = (SELECT id FROM types WHERE name = %s)
        """,
        ("Exhortación", "Encouragement", "Aliento", "Spiritual Gift"),
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        UPDATE gifts_passions
           SET name_es = %s
         WHERE name = %s
           AND name_es = %s
           AND type_id = (SELECT id FROM types WHERE name = %s)
        """,
        ("Aliento", "Encouragement", "Exhortación", "Spiritual Gift"),
    )
