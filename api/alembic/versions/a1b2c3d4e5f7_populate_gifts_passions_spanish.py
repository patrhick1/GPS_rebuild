"""populate gifts_passions Spanish descriptions from Sherri's 2026-05-05 PDF

Revision ID: a1b2c3d4e5f7
Revises: f9a0b1c2d3e4
Create Date: 2026-05-05 17:30:00.000000

Backfill content for the description_es column added in
[e8f9a0b1c2d3](e8f9a0b1c2d3_add_gifts_passion_description_es.py).
Source: GPS_Evaluacion_Espanol.pdf (Sherri Reishus, 2026-05-05).

Idempotent — only writes WHERE description_es IS NULL so re-running won't
clobber later edits made in the admin UI or by hand.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (gifts_passions.name, type_name) -> Spanish description
# Using both keys so a hypothetical future name collision (e.g., a future
# "Apostle" gift vs the existing "Apostle" influencing style) doesn't
# cross-write.
_SPANISH = {
    # Spiritual Gifts (19)
    ("Administration", "Spiritual Gift"): (
        "Capacidad de organizar recursos y coordinar detalles para un ministerio eficaz."
    ),
    ("Apostleship", "Spiritual Gift"): (
        "Capacidad de iniciar nuevas iglesias o misiones y supervisar su desarrollo."
    ),
    ("Craftsmanship", "Spiritual Gift"): (
        "Capacidad de diseñar o construir creativamente elementos para el ministerio."
    ),
    ("Creative Communication", "Spiritual Gift"): (
        "Capacidad de comunicar la verdad de Dios mediante el arte."
    ),
    ("Discernment", "Spiritual Gift"): (
        "Capacidad de distinguir verdad/error y juzgar según la Palabra de Dios."
    ),
    ("Encouragement", "Spiritual Gift"): (
        "Motivar a otros a vivir principios bíblicos y crecer en su fe."
    ),
    ("Evangelism", "Spiritual Gift"): (
        "Compartir el evangelio de forma efectiva e invitar a seguir a Jesús."
    ),
    ("Faith", "Spiritual Gift"): (
        "Confiar en Dios y actuar según sus promesas."
    ),
    ("Giving", "Spiritual Gift"): (
        "Contribuir generosamente para apoyar el ministerio."
    ),
    ("Hospitality", "Spiritual Gift"): (
        "Hacer que otros se sientan bienvenidos y aceptados."
    ),
    ("Intercession", "Spiritual Gift"): (
        "Orar constantemente por otros."
    ),
    ("Knowledge", "Spiritual Gift"): (
        "Entender e interpretar la verdad de Dios con claridad."
    ),
    ("Leadership", "Spiritual Gift"): (
        "Guiar y motivar a otros hacia metas ministeriales."
    ),
    ("Mercy", "Spiritual Gift"): (
        "Mostrar compasión y ayudar a quienes sufren."
    ),
    ("Prophecy", "Spiritual Gift"): (
        "Comunicar la Palabra de Dios con claridad y convicción."
    ),
    ("Service", "Spiritual Gift"): (
        "Satisfacer necesidades prácticas con alegría."
    ),
    ("Shepherding", "Spiritual Gift"): (
        "Cuidar y guiar espiritualmente a otros."
    ),
    ("Teaching", "Spiritual Gift"): (
        "Ayudar a otros a crecer mediante la Palabra de Dios."
    ),
    ("Wisdom", "Spiritual Gift"): (
        "Aplicar dirección espiritual en situaciones específicas."
    ),
    # Influencing Styles (5) — names in DB are singular ("Apostle"), PDF uses
    # plural ("Apóstoles"). Translate accordingly.
    ("Apostle", "Influencing Style"): (
        "Extienden el ministerio de Jesús."
    ),
    ("Prophet", "Influencing Style"): (
        "Comunican la voluntad de Dios."
    ),
    ("Evangelist", "Influencing Style"): (
        "Invitan a otros a la misión."
    ),
    ("Shepherd", "Influencing Style"): (
        "Cuidan a las personas."
    ),
    ("Teacher", "Influencing Style"): (
        "Enseñan la Palabra de Dios."
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    for (name, type_name), spanish in _SPANISH.items():
        bind.exec_driver_sql(
            """
            UPDATE gifts_passions
               SET description_es = %s
             WHERE name = %s
               AND description_es IS NULL
               AND type_id = (SELECT id FROM types WHERE name = %s)
            """,
            (spanish, name, type_name),
        )


def downgrade() -> None:
    # Reverse only what we set so we don't clobber any unrelated edits.
    bind = op.get_bind()
    for (name, type_name), spanish in _SPANISH.items():
        bind.exec_driver_sql(
            """
            UPDATE gifts_passions
               SET description_es = NULL
             WHERE name = %s
               AND description_es = %s
               AND type_id = (SELECT id FROM types WHERE name = %s)
            """,
            (name, spanish, type_name),
        )
