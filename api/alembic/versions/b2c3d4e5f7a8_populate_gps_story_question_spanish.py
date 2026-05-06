"""populate question_es for the 7 GPS story prompts

Revision ID: b2c3d4e5f7a8
Revises: a1b2c3d4e5f7
Create Date: 2026-05-05 18:30:00.000000

The seven GPS reflection-story questions (instrument_type='gps', type='Story',
order 3-9) shipped without Spanish translations. The grade endpoint already
returns `question_es`, and the results page already prefers it when locale=es,
so this is purely a content backfill.

Idempotent — only writes WHERE question_es IS NULL.

Translations align with the legacy GPS Spanish reflection prompts in
[es/assessment.php](../../../es/assessment.php) (e.g. the
`take-a-few-minutes-to-reflect-*` keys) but are tightened to match the
direct-question phrasing of the new platform's English copy.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (instrument_type, order) -> Spanish text
_SPANISH = {
    ("gps", 3): (
        "Revisa tus Dones Espirituales y sus definiciones. Comparte cualquier "
        "recuerdo que tengas de esos dones siendo usados o desarrollados en tu "
        "pasado."
    ),
    ("gps", 4): (
        "Revisa tus Habilidades. Comparte cualquier recuerdo que tengas de "
        "esas habilidades siendo usadas o desarrolladas en tu pasado."
    ),
    ("gps", 5): (
        "Revisa las Personas y las Causas que seleccionaste en la sección de "
        "Pasión. Por favor comparte experiencias de vida que potencialmente "
        "desarrollaron estas pasiones en ti. Como recordatorio, nuestras "
        "mayores pasiones suelen emerger de nuestras mayores luchas."
    ),
    ("gps", 6): (
        "Revisa tus Estilos de Influencia Espiritual. Comparte cualquier "
        "recuerdo que tengas de esos Estilos siendo usados o desarrollados en "
        "tu pasado."
    ),
    ("gps", 7): (
        "Si Dios te ofreciera hacer un cambio significativo en el mundo a "
        "través de tu vida, ¿qué cambio le pedirías que hiciera? Por favor sé "
        "específico."
    ),
    ("gps", 8): (
        "¿Qué dirían las personas más cercanas a ti que te apasiona?"
    ),
    ("gps", 9): (
        "Cuando te acerques al final de tu vida, ¿cuál es el único "
        "arrepentimiento (aparte de tu familia) del que quieres asegurarte de "
        "no tener?"
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    for (instrument, order), spanish in _SPANISH.items():
        bind.exec_driver_sql(
            """
            UPDATE questions
               SET question_es = %s
             WHERE instrument_type = %s
               AND "order" = %s
               AND question_es IS NULL
               AND type_id = (SELECT id FROM types WHERE name = 'Story')
            """,
            (spanish, instrument, order),
        )


def downgrade() -> None:
    bind = op.get_bind()
    for (instrument, order), spanish in _SPANISH.items():
        bind.exec_driver_sql(
            """
            UPDATE questions
               SET question_es = NULL
             WHERE instrument_type = %s
               AND "order" = %s
               AND question_es = %s
               AND type_id = (SELECT id FROM types WHERE name = 'Story')
            """,
            (instrument, order, spanish),
        )
