"""populate gifts_passions Spanish names

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-06-16 10:05:00.000000

Backfill content for the name_es column added in
[b6c7d8e9f0a1](b6c7d8e9f0a1_add_gifts_passion_name_es.py).

Source: conventional Spanish ministry vocabulary; pending Sherri's
brand-aligned review (2026-06-17). Reusing the same (name, type_name)
key shape as a1b2c3d4e5f7 so Apostle (style) vs a hypothetical Apostle
(gift) can't cross-write.

Idempotent — only writes WHERE name_es IS NULL so a re-run after
Sherri tweaks a value in the admin UI won't clobber the edit.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SPANISH_NAMES = {
    # Spiritual Gifts (19)
    ("Administration", "Spiritual Gift"): "Administración",
    ("Apostleship", "Spiritual Gift"): "Apostolado",
    ("Craftsmanship", "Spiritual Gift"): "Artesanía",
    ("Creative Communication", "Spiritual Gift"): "Comunicación Creativa",
    ("Discernment", "Spiritual Gift"): "Discernimiento",
    ("Encouragement", "Spiritual Gift"): "Aliento",
    ("Evangelism", "Spiritual Gift"): "Evangelismo",
    ("Faith", "Spiritual Gift"): "Fe",
    ("Giving", "Spiritual Gift"): "Generosidad",
    ("Hospitality", "Spiritual Gift"): "Hospitalidad",
    ("Intercession", "Spiritual Gift"): "Intercesión",
    ("Knowledge", "Spiritual Gift"): "Conocimiento",
    ("Leadership", "Spiritual Gift"): "Liderazgo",
    ("Mercy", "Spiritual Gift"): "Misericordia",
    ("Prophecy", "Spiritual Gift"): "Profecía",
    ("Service", "Spiritual Gift"): "Servicio",
    ("Shepherding", "Spiritual Gift"): "Pastoreo",
    ("Teaching", "Spiritual Gift"): "Enseñanza",
    ("Wisdom", "Spiritual Gift"): "Sabiduría",
    # Influencing Styles (5)
    ("Apostle", "Influencing Style"): "Apóstol",
    ("Prophet", "Influencing Style"): "Profeta",
    ("Evangelist", "Influencing Style"): "Evangelista",
    ("Shepherd", "Influencing Style"): "Pastor",
    ("Teacher", "Influencing Style"): "Maestro",
}


def upgrade() -> None:
    bind = op.get_bind()
    for (name, type_name), spanish in _SPANISH_NAMES.items():
        bind.exec_driver_sql(
            """
            UPDATE gifts_passions
               SET name_es = %s
             WHERE name = %s
               AND name_es IS NULL
               AND type_id = (SELECT id FROM types WHERE name = %s)
            """,
            (spanish, name, type_name),
        )


def downgrade() -> None:
    bind = op.get_bind()
    for (name, type_name), spanish in _SPANISH_NAMES.items():
        bind.exec_driver_sql(
            """
            UPDATE gifts_passions
               SET name_es = NULL
             WHERE name = %s
               AND name_es = %s
               AND type_id = (SELECT id FROM types WHERE name = %s)
            """,
            (name, spanish, type_name),
        )
