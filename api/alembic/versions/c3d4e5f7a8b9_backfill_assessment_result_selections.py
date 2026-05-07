"""backfill abilities / people / cause on existing GPS AssessmentResult rows

Revision ID: c3d4e5f7a8b9
Revises: b2c3d4e5f7a8
Create Date: 2026-05-07 00:00:00.000000

For ~five months ScoringService stored hardcoded Laravel-era order numbers
(166 / 157 / 158) for the three multi-select GPS questions, but those orders
don't exist in the new schema. Result: every AssessmentResult.abilities,
.people, and .cause was saved as an empty string, even though the wizard
correctly captured the user's selections in the answers table.

Caught 2026-05-07 when Sherri reported the Key Abilities / People / Causes
panels on the results page were empty. Code fix lands alongside this
migration; this migration recovers the historical data by re-reading from
the answers table.

Idempotent: only writes rows where the target column is NULL or empty.
Doesn't touch rows that already have a value (e.g. anything created after
the code fix takes effect).

Reversible: downgrade nulls only the rows we set in upgrade.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (column_on_assessment_results, GPS question type, order)
# `order` alone is ambiguous (likert and multiple_choice share orders 1, 2,
# and 77), so we disambiguate by the question's type + question_type as well.
_FIELD_TO_LOOKUP = [
    ("people", "Influencing Style", 1),
    ("cause", "Influencing Style", 2),
    ("abilities", "Spiritual Gift", 77),
]


def _resolve_question_id(bind, type_name: str, order: int):
    row = bind.exec_driver_sql(
        """
        SELECT q.id
          FROM questions q
          JOIN types t ON t.id = q.type_id
          JOIN question_types qt ON qt.id = q.question_type_id
         WHERE q.instrument_type = 'gps'
           AND t.name = %s
           AND qt.type = 'multiple_choice'
           AND q."order" = %s
         LIMIT 1
        """,
        (type_name, order),
    ).fetchone()
    return row[0] if row else None


def upgrade() -> None:
    bind = op.get_bind()
    for column, type_name, order in _FIELD_TO_LOOKUP:
        question_id = _resolve_question_id(bind, type_name, order)
        if not question_id:
            continue
        # For each AssessmentResult whose target column is empty, copy the
        # corresponding answer.multiple_choice_answer over. The string is
        # already comma-joined the way the runtime code stores it.
        bind.exec_driver_sql(
            f"""
            UPDATE assessment_results r
               SET {column} = ans.multiple_choice_answer
              FROM answers ans
              JOIN assessments a ON a.id = ans.assessment_id
             WHERE r.assessment_id = a.id
               AND a.instrument_type = 'gps'
               AND ans.question_id = %s
               AND ans.multiple_choice_answer IS NOT NULL
               AND ans.multiple_choice_answer <> ''
               AND coalesce(r.{column}, '') = ''
            """,
            (str(question_id),),
        )


def downgrade() -> None:
    bind = op.get_bind()
    for column, type_name, order in _FIELD_TO_LOOKUP:
        question_id = _resolve_question_id(bind, type_name, order)
        if not question_id:
            continue
        # Reverse only rows whose value matches what the corresponding
        # answer holds, so any later hand-edits aren't clobbered.
        bind.exec_driver_sql(
            f"""
            UPDATE assessment_results r
               SET {column} = NULL
              FROM answers ans
              JOIN assessments a ON a.id = ans.assessment_id
             WHERE r.assessment_id = a.id
               AND a.instrument_type = 'gps'
               AND ans.question_id = %s
               AND ans.multiple_choice_answer = r.{column}
            """,
            (str(question_id),),
        )
