"""Smoke tests — live (DB + network)."""
print("[start]", flush=True)
import sys, os, traceback, hashlib, hmac, json, time
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

import httpx
import psycopg2

from app.services.webhook_payloads import build_test_assessment_payload

PASS = 0
FAIL = 0


def run(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  PASS  {name}", flush=True)
    except AssertionError as e:
        FAIL += 1
        print(f"  FAIL  {name}: {e}", flush=True)
    except Exception:
        FAIL += 1
        print(f"  FAIL  {name}: {traceback.format_exc().splitlines()[-1]}", flush=True)


def conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=15)


# -------- live HTTP delivery
print("[live-http]", flush=True)


def t_httpbin_delivery():
    payload = build_test_assessment_payload(event_type="assessment_completed")
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-GPS-Event": "assessment_completed",
        "X-GPS-Test": "true",
    }
    secret = "smoke-test-secret"
    headers["X-GPS-Signature"] = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    with httpx.Client(timeout=20.0) as client:
        resp = client.post("https://httpbin.org/post", content=body, headers=headers)
    assert 200 <= resp.status_code < 300, f"HTTP {resp.status_code}"
    echoed = resp.json()
    # httpbin echoes the request body back under .json and headers under .headers
    assert echoed["json"]["test"] is True, "echoed test flag missing"
    assert echoed["headers"].get("X-Gps-Event") == "assessment_completed", echoed["headers"]
    assert echoed["headers"].get("X-Gps-Signature", "").startswith("sha256="), echoed["headers"]


run("POST to httpbin.org with signed body returns 2xx + echo intact", t_httpbin_delivery)


# -------- DB schema integrity
print("[db-schema]", flush=True)


def t_alembic_head():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        head = cur.fetchone()[0]
        assert head == "f9a0b1c2d3e4", f"head={head}"


def t_notifications_is_read_boolean():
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='notifications' AND column_name='is_read'"
        )
        assert cur.fetchone()[0] == "boolean"


def t_notifications_reference_cols():
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='notifications' AND column_name IN ('reference_type','reference_id')"
        )
        cols = {r[0] for r in cur.fetchall()}
        assert cols == {"reference_type", "reference_id"}, cols


def t_webhook_configs_unique():
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid='webhook_configs'::regclass AND contype='u'"
        )
        names = [r[0] for r in cur.fetchall()]
        assert "uq_webhook_configs_org_event" in names


def t_webhook_deliveries_indexes():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT indexname FROM pg_indexes WHERE tablename='webhook_deliveries'")
        idx = {r[0] for r in cur.fetchall()}
        assert "ix_webhook_deliveries_status_next_retry" in idx
        assert "ix_webhook_deliveries_config_created" in idx


def t_gifts_passions_description_es():
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT data_type, is_nullable FROM information_schema.columns "
            "WHERE table_name='gifts_passions' AND column_name='description_es'"
        )
        row = cur.fetchone()
        assert row is not None and row[0] == "text" and row[1] == "YES"


def t_myimpact_spanish_count():
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM questions "
            "WHERE instrument_type='myimpact' AND question_es IS NOT NULL"
        )
        assert cur.fetchone()[0] == 17


def t_myimpact_spanish_text_intact():
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT question_es FROM questions "
            "WHERE instrument_type='myimpact' AND section='Character' AND \"order\"=1"
        )
        text = cur.fetchone()[0]
        assert text.startswith("Soy una persona amorosa"), repr(text[:80])
        assert "amo" in text.lower(), repr(text[:80])


run("alembic_version is f9a0b1c2d3e4", t_alembic_head)
run("notifications.is_read is BOOLEAN", t_notifications_is_read_boolean)
run("notifications has reference_type + reference_id", t_notifications_reference_cols)
run("webhook_configs UNIQUE (org_id, event_type)", t_webhook_configs_unique)
run("webhook_deliveries has status+retry index", t_webhook_deliveries_indexes)
run("gifts_passions.description_es exists, nullable, text", t_gifts_passions_description_es)
run("17 MyImpact questions backfilled", t_myimpact_spanish_count)
run("MyImpact Spanish text intact (UTF-8)", t_myimpact_spanish_text_intact)


# -------- retry runner SQL parses + finds nothing
print("[retry-runner]", flush=True)


def t_retry_runner_query():
    """Verify the SQL parses and returns 0 (no failed rows in DB).
    We open a fresh psycopg2 conn — not a SQLAlchemy session — to avoid
    the heavy import chain that hung the original combined script."""
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT id FROM webhook_deliveries "
            " WHERE status = 'failed' "
            "   AND next_retry_at <= NOW() "
            "   AND attempts < 3 "
            " ORDER BY next_retry_at ASC "
            " LIMIT 50 "
            " FOR UPDATE SKIP LOCKED"
        )
        rows = cur.fetchall()
        assert len(rows) == 0, f"unexpected pending rows: {rows}"


run("process_pending_retries SQL returns 0 cleanly", t_retry_runner_query)


# -------- i18n coverage
print("[i18n]", flush=True)


def t_translations_count():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "web", "src", "i18n", "translations.ts")
    )
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    es_block = content.split("const es: Record<string, string> = {", 1)[1].split("\n};", 1)[0]
    # Heuristic: count lines that contain ': ' with a leading quoted key.
    entries = sum(
        1 for line in es_block.splitlines()
        if ("'" in line or '"' in line) and ":" in line and not line.strip().startswith("//")
    )
    assert entries >= 50, f"only {entries} entries"


def t_useTranslation_hook_exists():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "web", "src", "hooks", "useTranslation.ts")
    )
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "export function useTranslation" in content
    assert "interpolate" in content, "interpolation helper missing"


run("translations.ts has 50+ Spanish entries", t_translations_count)
run("useTranslation hook exports + has interpolation", t_useTranslation_hook_exists)


print(f"\n[summary] PASS={PASS} FAIL={FAIL}", flush=True)
sys.exit(0 if FAIL == 0 else 1)
