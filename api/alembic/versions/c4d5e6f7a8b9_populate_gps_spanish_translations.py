"""populate gps spanish translations

Revision ID: c4d5e6f7a8b9
Revises: b3c1d2e4f5a6
Create Date: 2026-04-13 00:00:00.000000

"""
from typing import Sequence, Union
import csv
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b3c1d2e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Minimal table references for the data migration
types_table = sa.table('types', sa.column('id'), sa.column('name'))
questions_table = sa.table(
    'questions',
    sa.column('id'),
    sa.column('question_es'),
    sa.column('type_id'),
    sa.column('instrument_type'),
    sa.column('order', sa.Integer),
)


def _find_csv():
    """Locate gps_questions_spanish.csv relative to this migration file."""
    # migrations live in api/alembic/versions/  →  repo root is ../../../
    base = os.path.dirname(__file__)
    for rel in [
        os.path.join(base, '..', '..', '..', 'gps_questions_spanish.csv'),
        os.path.join(base, '..', '..', '..', '..', 'gps_questions_spanish.csv'),
    ]:
        p = os.path.normpath(rel)
        if os.path.exists(p):
            return p
    return None


def upgrade() -> None:
    csv_path = _find_csv()
    if csv_path is None:
        print("WARNING: gps_questions_spanish.csv not found — skipping Spanish translation population")
        return

    bind = op.get_bind()
    session = Session(bind=bind)

    # Look up type IDs by name
    gift_type = session.execute(
        sa.select(types_table.c.id).where(types_table.c.name == 'Spiritual Gift')
    ).scalar()
    infl_type = session.execute(
        sa.select(types_table.c.id).where(types_table.c.name == 'Influencing Style')
    ).scalar()

    if not gift_type or not infl_type:
        print("WARNING: Required types not found — skipping Spanish translation population")
        return

    # Build ordered lists of GPS questions per type
    def get_ordered_ids(type_id):
        rows = session.execute(
            sa.select(questions_table.c.id)
            .where(questions_table.c.instrument_type == 'gps')
            .where(questions_table.c.type_id == type_id)
            .order_by(questions_table.c.order)
        ).fetchall()
        return {i + 1: row[0] for i, row in enumerate(rows)}

    section_map = {
        'Gifts': get_ordered_ids(gift_type),
        'Influencing Style': get_ordered_ids(infl_type),
    }

    updated = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            section = row['Section'].strip()
            spanish_text = row['Spanish'].strip()
            if not spanish_text:
                continue
            try:
                num = int(row['Question'])
            except (ValueError, KeyError):
                continue
            q_id = section_map.get(section, {}).get(num)
            if q_id:
                session.execute(
                    questions_table.update()
                    .where(questions_table.c.id == q_id)
                    .values(question_es=spanish_text)
                )
                updated += 1

    session.commit()
    print(f"Updated {updated} GPS questions with Spanish translations")


def downgrade() -> None:
    # Clear all question_es values for GPS questions
    bind = op.get_bind()
    session = Session(bind=bind)
    session.execute(
        questions_table.update()
        .where(questions_table.c.instrument_type == 'gps')
        .values(question_es=None)
    )
    session.commit()
