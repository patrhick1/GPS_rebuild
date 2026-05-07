"""rename "Regional, State or Federal Issues" cause option (drop embedded comma)

Revision ID: d4e5f7a8b9c0
Revises: c3d4e5f7a8b9
Create Date: 2026-05-07 00:30:00.000000

The cause option `Regional, State or Federal Issues` had an embedded comma,
which collided with the comma-joined storage format used for
`answers.multiple_choice_answer` and `assessment_results.cause`. When the
results page split the saved string on commas it produced three pills
("Regional", "State or Federal Issues", "Homelessness") instead of two
("Regional/State/Federal Issues", "Homelessness").

The frontend option label has been renamed to `Regional/State/Federal Issues`
(matching siblings like `Disabilities and/or Support`) so future submissions
store a comma-free string. This migration rewrites the historical data so
the same row's pills show correctly without re-submitting.

Idempotent — only updates rows that still contain the legacy substring.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f7a8b9c0"
down_revision: Union[str, None] = "c3d4e5f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD = "Regional, State or Federal Issues"
_NEW = "Regional/State/Federal Issues"


def upgrade() -> None:
    bind = op.get_bind()
    # Update raw answer strings.
    bind.exec_driver_sql(
        """
        UPDATE answers
           SET multiple_choice_answer = REPLACE(multiple_choice_answer, %s, %s)
         WHERE multiple_choice_answer LIKE %s
        """,
        (_OLD, _NEW, f"%{_OLD}%"),
    )
    # And the materialized assessment_results.cause column.
    bind.exec_driver_sql(
        """
        UPDATE assessment_results
           SET cause = REPLACE(cause, %s, %s)
         WHERE cause LIKE %s
        """,
        (_OLD, _NEW, f"%{_OLD}%"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        UPDATE answers
           SET multiple_choice_answer = REPLACE(multiple_choice_answer, %s, %s)
         WHERE multiple_choice_answer LIKE %s
        """,
        (_NEW, _OLD, f"%{_NEW}%"),
    )
    bind.exec_driver_sql(
        """
        UPDATE assessment_results
           SET cause = REPLACE(cause, %s, %s)
         WHERE cause LIKE %s
        """,
        (_NEW, _OLD, f"%{_NEW}%"),
    )
