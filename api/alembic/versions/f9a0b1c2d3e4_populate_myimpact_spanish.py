"""populate myimpact question_es from es/SPANISH - MYIMPACT ASSESSMENT.md

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-05-01 12:30:00.000000

Phase D content backfill: Spanish text for the 9 Character + 8 Calling MyImpact
questions. Source is the spec authored by Chelsie Carroll on 2026-04-22 at
[es/SPANISH - MYIMPACT ASSESSMENT.md](../../../es/SPANISH%20-%20MYIMPACT%20ASSESSMENT.md).

Each Spanish translation combines the prompt and the italicized explanation
from the markdown so the structure mirrors the English text loaded by
`db_seed.py` from `myimpact_questions.csv`. Character rows have order 1-9;
Calling rows have order 10-17 (sort_order 1-8 + 9 offset).

This migration is *idempotent* — uses `WHERE question_es IS NULL` so
re-running won't clobber any later edits.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (section, order) -> Spanish text
_SPANISH = {
    ("Character", 1): (
        "Soy una persona amorosa. Amo a todas las personas incondicionalmente, "
        "como Dios me ama a mí."
    ),
    ("Character", 2): (
        "Soy una persona gozosa. El gozo es mi disposición dominante, "
        "incluso en tiempos difíciles."
    ),
    ("Character", 3): (
        "Soy una persona pacífica. Experimento paz internamente y en la "
        "mayoría de mis relaciones."
    ),
    ("Character", 4): (
        "Soy una persona paciente. Soporto situaciones desafiantes sin "
        "perder la compostura."
    ),
    ("Character", 5): (
        "Soy una persona amable. Trato a los demás con amabilidad y dignidad."
    ),
    ("Character", 6): (
        "Soy una buena persona. Mis acciones hacia los demás son buenas "
        "por naturaleza."
    ),
    ("Character", 7): (
        "Soy una persona fiel. La gente puede contar conmigo porque yo "
        "cuento completamente con Dios."
    ),
    ("Character", 8): (
        "Soy una persona gentil. Soy una persona de fuerza que reserva mi "
        "fuerza para el bien."
    ),
    ("Character", 9): (
        "Soy una persona con autocontrol. No soy propenso a comportamientos "
        "excesivos o impulsivos."
    ),
    ("Calling", 10): (
        "Puedo nombrar mis 3 Dones Espirituales principales. Dios, de su gran "
        "variedad de dones espirituales, les ha dado un don a cada uno de "
        "ustedes. Úsenlos bien para servirse los unos a los otros."
    ),
    ("Calling", 11): (
        "Conozco a las personas o causas específicas a las que Dios quiere "
        "que sirva. p. ej., adolescentes, personas sin hogar, el "
        "analfabetismo, padres solteros."
    ),
    ("Calling", 12): (
        "Actualmente estoy utilizando mis mejores dones para servir a las "
        "personas a las que Dios quiere que sirva. Por ejemplo, utilizando "
        "mis dones de administración y misericordia para servir en un banco "
        "de alimentos local."
    ),
    ("Calling", 13): (
        "Regularmente veo a Dios haciendo una diferencia en la vida de los "
        "demás cuando uso mis dones para servirles."
    ),
    ("Calling", 14): (
        "Experimento una alegría significativa cuando uso mis dones para "
        "servir a los demás."
    ),
    ("Calling", 15): (
        "Regularmente oro por las personas con las que vivo, trabajo, estudio "
        "y me divierto. Estas oraciones a menudo me brindan la oportunidad de "
        "servirles y compartir con ellas mi historia de fe."
    ),
    ("Calling", 16): (
        "Regularmente veo personas pasar de la indiferencia espiritual a la fe "
        "mientras les sirvo y comparto mi historia con ellos."
    ),
    ("Calling", 17): (
        "Recibo apoyo y aliento constantes mientras me esfuerzo por crecer en "
        "mi llamado personal."
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    for (section, order), spanish in _SPANISH.items():
        bind.exec_driver_sql(
            "UPDATE questions "
            "SET question_es = %s "
            "WHERE instrument_type = 'myimpact' "
            "  AND section = %s "
            "  AND \"order\" = %s "
            "  AND question_es IS NULL",
            (spanish, section, order),
        )


def downgrade() -> None:
    # Reverse only what we set so we don't clobber any unrelated edits.
    bind = op.get_bind()
    for (section, order), spanish in _SPANISH.items():
        bind.exec_driver_sql(
            "UPDATE questions "
            "SET question_es = NULL "
            "WHERE instrument_type = 'myimpact' "
            "  AND section = %s "
            "  AND \"order\" = %s "
            "  AND question_es = %s",
            (section, order, spanish),
        )
