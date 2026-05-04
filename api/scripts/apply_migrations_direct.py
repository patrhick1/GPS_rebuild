"""Apply pending migrations directly via psycopg2 because the alembic
CLI / Python API hangs in this dev environment for unclear reasons
(suspected: subprocess + Windows + alembic interaction).

Applies (in order):
  a1b2c3d4e5f6 -> b5d1f0e2a3c4  (add webhook_events)
  b5d1f0e2a3c4 -> c6a7b8d9e0f1  (reconcile notifications)
  c6a7b8d9e0f1 -> d7e8f9a0b1c2  (add webhook_configs and webhook_deliveries)
  d7e8f9a0b1c2 -> e8f9a0b1c2d3  (add gifts_passions.description_es)
  e8f9a0b1c2d3 -> f9a0b1c2d3e4  (populate myimpact question_es)

Idempotent: checks alembic_version before each step.
"""
import os
import sys
import time

from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]


WEBHOOK_EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY,
    stripe_event_id VARCHAR(255) NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_webhook_events_event_type_processed_at
    ON webhook_events (event_type, processed_at);
"""

# Two-step Postgres column type swap is wrapped in a single tx.
RECONCILE_NOTIFICATIONS_SQL = """
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS reference_type VARCHAR(50);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS reference_id UUID;

DROP INDEX IF EXISTS ix_notifications_user_read_created;

ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS is_read_bool BOOLEAN NOT NULL DEFAULT false;

UPDATE notifications SET is_read_bool = (is_read = 'Y');

ALTER TABLE notifications DROP COLUMN is_read;
ALTER TABLE notifications RENAME COLUMN is_read_bool TO is_read;

CREATE INDEX ix_notifications_user_read_created
    ON notifications (user_id, is_read, created_at);

UPDATE notifications
   SET type = 'assessment_self_completed'
 WHERE type IN ('gps_result', 'myimpact_result');
"""


WEBHOOK_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS webhook_configs (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    webhook_url VARCHAR(2048) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    secret VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_webhook_configs_org_event UNIQUE (organization_id, event_type)
);
CREATE INDEX IF NOT EXISTS ix_webhook_configs_org_active
    ON webhook_configs (organization_id, is_active);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY,
    webhook_config_id UUID NOT NULL REFERENCES webhook_configs(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    http_status_code SMALLINT,
    error_message TEXT,
    attempts SMALLINT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_status_next_retry
    ON webhook_deliveries (status, next_retry_at);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_config_created
    ON webhook_deliveries (webhook_config_id, created_at);
"""


GIFTS_DESCRIPTION_ES_SQL = """
ALTER TABLE gifts_passions ADD COLUMN IF NOT EXISTS description_es TEXT;
"""


# Spanish text for the 17 MyImpact questions, sourced from
# es/SPANISH - MYIMPACT ASSESSMENT.md (Chelsie Carroll, 2026-04-22).
_MYIMPACT_SPANISH = [
    ("Character", 1,  "Soy una persona amorosa. Amo a todas las personas incondicionalmente, como Dios me ama a mí."),
    ("Character", 2,  "Soy una persona gozosa. El gozo es mi disposición dominante, incluso en tiempos difíciles."),
    ("Character", 3,  "Soy una persona pacífica. Experimento paz internamente y en la mayoría de mis relaciones."),
    ("Character", 4,  "Soy una persona paciente. Soporto situaciones desafiantes sin perder la compostura."),
    ("Character", 5,  "Soy una persona amable. Trato a los demás con amabilidad y dignidad."),
    ("Character", 6,  "Soy una buena persona. Mis acciones hacia los demás son buenas por naturaleza."),
    ("Character", 7,  "Soy una persona fiel. La gente puede contar conmigo porque yo cuento completamente con Dios."),
    ("Character", 8,  "Soy una persona gentil. Soy una persona de fuerza que reserva mi fuerza para el bien."),
    ("Character", 9,  "Soy una persona con autocontrol. No soy propenso a comportamientos excesivos o impulsivos."),
    ("Calling",   10, "Puedo nombrar mis 3 Dones Espirituales principales. Dios, de su gran variedad de dones espirituales, les ha dado un don a cada uno de ustedes. Úsenlos bien para servirse los unos a los otros."),
    ("Calling",   11, "Conozco a las personas o causas específicas a las que Dios quiere que sirva. p. ej., adolescentes, personas sin hogar, el analfabetismo, padres solteros."),
    ("Calling",   12, "Actualmente estoy utilizando mis mejores dones para servir a las personas a las que Dios quiere que sirva. Por ejemplo, utilizando mis dones de administración y misericordia para servir en un banco de alimentos local."),
    ("Calling",   13, "Regularmente veo a Dios haciendo una diferencia en la vida de los demás cuando uso mis dones para servirles."),
    ("Calling",   14, "Experimento una alegría significativa cuando uso mis dones para servir a los demás."),
    ("Calling",   15, "Regularmente oro por las personas con las que vivo, trabajo, estudio y me divierto. Estas oraciones a menudo me brindan la oportunidad de servirles y compartir con ellas mi historia de fe."),
    ("Calling",   16, "Regularmente veo personas pasar de la indiferencia espiritual a la fe mientras les sirvo y comparto mi historia con ellos."),
    ("Calling",   17, "Recibo apoyo y aliento constantes mientras me esfuerzo por crecer en mi llamado personal."),
]



def current_head(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
        return row[0] if row else None


def set_head(conn, head):
    with conn.cursor() as cur:
        cur.execute("UPDATE alembic_version SET version_num = %s", (head,))


REV_ORDER = [
    "a1b2c3d4e5f6",
    "b5d1f0e2a3c4",
    "c6a7b8d9e0f1",
    "d7e8f9a0b1c2",
    "e8f9a0b1c2d3",
    "f9a0b1c2d3e4",
]


def _rev_index(rev):
    try:
        return REV_ORDER.index(rev)
    except ValueError:
        return -1


def run_step(conn, from_rev, to_rev, sql, label):
    head = current_head(conn)
    head_idx = _rev_index(head)
    target_idx = _rev_index(to_rev)
    if head_idx >= target_idx:
        print(f"[skip] head {head} >= {to_rev} ({label})")
        return
    if head != from_rev:
        raise RuntimeError(
            f"Expected head {from_rev}, found {head}. Aborting {label}."
        )
    print(f"[apply] {from_rev} -> {to_rev} ({label})")
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("UPDATE alembic_version SET version_num = %s", (to_rev,))
    conn.commit()
    print(f"  ok in {time.time()-t0:.2f}s")


def main():
    print(f"Connecting to {DATABASE_URL[:50]}...", flush=True)
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
    try:
        head = current_head(conn)
        print(f"Current head: {head}", flush=True)

        run_step(
            conn,
            "a1b2c3d4e5f6",
            "b5d1f0e2a3c4",
            WEBHOOK_EVENTS_SQL,
            "add webhook_events",
        )
        run_step(
            conn,
            "b5d1f0e2a3c4",
            "c6a7b8d9e0f1",
            RECONCILE_NOTIFICATIONS_SQL,
            "reconcile notifications",
        )
        run_step(
            conn,
            "c6a7b8d9e0f1",
            "d7e8f9a0b1c2",
            WEBHOOK_TABLES_SQL,
            "add webhook_configs and webhook_deliveries",
        )
        run_step(
            conn,
            "d7e8f9a0b1c2",
            "e8f9a0b1c2d3",
            GIFTS_DESCRIPTION_ES_SQL,
            "add gifts_passions.description_es",
        )

        # Phase D Spanish backfill — multi-row, so handled outside run_step
        # to use parameterized queries cleanly.
        head = current_head(conn)
        if _rev_index(head) < _rev_index("f9a0b1c2d3e4"):
            if head != "e8f9a0b1c2d3":
                raise RuntimeError(
                    f"Expected head e8f9a0b1c2d3, found {head}. Aborting MyImpact backfill."
                )
            print("[apply] e8f9a0b1c2d3 -> f9a0b1c2d3e4 (populate myimpact question_es)")
            t0 = time.time()
            with conn.cursor() as cur:
                updated = 0
                for section, order, spanish in _MYIMPACT_SPANISH:
                    cur.execute(
                        "UPDATE questions "
                        "SET question_es = %s "
                        "WHERE instrument_type = 'myimpact' "
                        "  AND section = %s "
                        '  AND "order" = %s '
                        "  AND question_es IS NULL",
                        (spanish, section, order),
                    )
                    updated += cur.rowcount
                cur.execute(
                    "UPDATE alembic_version SET version_num = %s", ("f9a0b1c2d3e4",)
                )
            conn.commit()
            print(f"  ok in {time.time()-t0:.2f}s ({updated} rows updated)")
        else:
            print(f"[skip] head {head} >= f9a0b1c2d3e4 (populate myimpact question_es)")

        head = current_head(conn)
        print(f"Final head: {head}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
