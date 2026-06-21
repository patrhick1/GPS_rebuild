"""populate default_text_es for MyImpact verse captions

Revision ID: 6559048b8846
Revises: 6d097c824704
Create Date: 2026-06-21 00:00:00.000000

User report 2026-06-21: per-question Bible verse caption on the MyImpact
wizard stays English even in Spanish mode. Root cause was three-fold —
schema didn't expose default_text_es, frontend type didn't include it,
render sites didn't use the isEs fallback. Code fixes shipped alongside.

This migration plugs the underlying data gap: questions.default_text_es
was NULL for every MyImpact row. Only 2 distinct default_text values
exist across all MyImpact questions:

  Character section (order ≤ 9):  Galatians 5:22-23
  Calling section   (order ≥ 10): Ephesians 2:10

Spanish text mirrors the same translations Sherri previously approved
for the section header description in MyImpactWizard.tsx (NVI / common
Christian-Spanish renderings).

LIKE prefix match on default_text so this is resilient to small
punctuation variations between rows.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "6559048b8846"
down_revision: Union[str, None] = "6d097c824704"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GALATIANS_ES = (
    "En cambio, el fruto del Espíritu es amor, alegría, paz, paciencia, "
    "amabilidad, bondad, fidelidad, humildad y dominio propio. Gálatas 5:22-23"
)
EPHESIANS_ES = (
    "Porque somos hechura de Dios, creados en Cristo Jesús para buenas obras, "
    "las cuales Dios dispuso de antemano a fin de que las pongamos en práctica. "
    "Efesios 2:10"
)


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        UPDATE questions
           SET default_text_es = %s
         WHERE instrument_type = 'myimpact'
           AND default_text_es IS NULL
           AND default_text LIKE 'But the Holy Spirit produces%%'
        """,
        (GALATIANS_ES,),
    )
    bind.exec_driver_sql(
        """
        UPDATE questions
           SET default_text_es = %s
         WHERE instrument_type = 'myimpact'
           AND default_text_es IS NULL
           AND default_text LIKE 'We are God''s handiwork%%'
        """,
        (EPHESIANS_ES,),
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        UPDATE questions
           SET default_text_es = NULL
         WHERE instrument_type = 'myimpact'
           AND default_text_es IN (%s, %s)
        """,
        (GALATIANS_ES, EPHESIANS_ES),
    )
