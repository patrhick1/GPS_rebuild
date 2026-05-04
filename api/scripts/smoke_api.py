"""HTTP-layer smoke driver — exercises SMOKE_TEST_GUIDE.md items via the live API.

Run after `uvicorn app.main:app --host 127.0.0.1 --port 8000` is up.
Reads WEBHOOK_SITE_URL from the environment for B2/B3/B4 inbox inspection.
Reads INTERNAL_CRON_SECRET from api/.env for B6/B7.

Test data: uses seeded users (db_seed.py — admin1@test.com, admin2@test.com,
admin2nd@test.com, member1@test.com, user1@test.com, master@test.com — all
TestPass#2024). Test Church 1 has key=test-church-1.

Side effects: creates webhook configs, registers transient users with
+smoke<hex>@ tags, submits assessments. Cleans up at the end.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()  # picks up INTERNAL_CRON_SECRET

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")
WEBHOOK_SITE_URL = os.environ.get("WEBHOOK_SITE_URL", "").rstrip("/")
WEBHOOK_TOKEN = WEBHOOK_SITE_URL.rsplit("/", 1)[-1] if WEBHOOK_SITE_URL else ""
WEBHOOK_INSPECT = (
    f"https://webhook.site/token/{WEBHOOK_TOKEN}/requests" if WEBHOOK_TOKEN else None
)
CRON_SECRET = os.environ.get("INTERNAL_CRON_SECRET", "")

PASS = 0
FAIL = 0
SKIP = 0
RESULTS: list[tuple[str, str, str]] = []  # (status, name, detail)


def _emit(status: str, name: str, detail: str = "") -> None:
    global PASS, FAIL, SKIP
    if status == "PASS":
        PASS += 1
    elif status == "FAIL":
        FAIL += 1
    else:
        SKIP += 1
    print(f"  {status:4} {name}" + (f" — {detail}" if detail else ""), flush=True)
    RESULTS.append((status, name, detail))


def run(name: str, fn):
    try:
        fn()
        _emit("PASS", name)
    except AssertionError as e:
        _emit("FAIL", name, str(e))
    except Exception as e:
        _emit("FAIL", name, f"{type(e).__name__}: {e}")


def skip(name: str, reason: str) -> None:
    _emit("SKIP", name, reason)


# ---------- helpers ----------

def login(email: str, pw: str = "TestPass#2024") -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"login {email} -> {r.status_code} {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def me(sess: requests.Session) -> dict:
    return sess.get(f"{API}/auth/me", timeout=10).json()


def fetch_questions(sess: requests.Session, instrument: str) -> dict:
    r = sess.post(
        f"{API}/assessments/start",
        params={"instrument_type": instrument},
        timeout=15,
    )
    assert r.status_code in (200, 201), f"start {instrument}: {r.status_code} {r.text[:200]}"
    return r.json()


def fabricate_answers(form: dict) -> list[dict]:
    """Build a deterministic answer set for either GPS or MyImpact."""
    out = []
    for q in form["questions"]:
        qtype = q.get("question_type_name") or ""
        ans = {"question_id": q["id"]}
        if qtype == "likert":
            ans["numeric_value"] = 4
        elif qtype == "multiple_choice":
            # GPS multi-selects (people, causes, abilities) accept comma-separated
            # values per the existing wizard behaviour; pick a generic single choice.
            ans["multiple_choice_answer"] = "A"
        elif qtype == "text":
            ans["text_value"] = "Smoke test answer."
        else:
            # Default to a numeric value if unknown — server tolerates extras.
            ans["numeric_value"] = 3
        out.append(ans)
    return out


def submit_assessment(sess: requests.Session, instrument: str = "gps") -> dict:
    form = fetch_questions(sess, instrument)
    answers = fabricate_answers(form)
    r = sess.post(
        f"{API}/assessments/{form['assessment_id']}/submit",
        json={"answers": answers},
        timeout=30,
    )
    assert r.status_code == 200, f"submit: {r.status_code} {r.text[:300]}"
    return {"assessment_id": form["assessment_id"], "result": r.json()}


def webhook_site_clear() -> None:
    if not WEBHOOK_TOKEN:
        return
    try:
        requests.delete(
            f"https://webhook.site/token/{WEBHOOK_TOKEN}/request",
            timeout=10,
        )
    except Exception:
        pass


def webhook_site_wait(predicate, timeout: int = 20) -> dict | None:
    """Poll webhook.site for a request matching predicate(req_dict)."""
    if not WEBHOOK_INSPECT:
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(WEBHOOK_INSPECT, params={"sorting": "newest"}, timeout=10)
            if r.status_code == 200:
                for req in r.json().get("data", []):
                    if predicate(req):
                        return req
        except Exception:
            pass
        time.sleep(1.5)
    return None


def get_admin_org_id(sess: requests.Session) -> str:
    """Read admin's org_id via /admin/settings (works for any admin role)."""
    r = sess.get(f"{API}/admin/settings", timeout=10)
    assert r.status_code == 200, f"admin/settings -> {r.status_code} {r.text[:200]}"
    body = r.json()
    return body.get("organization_id") or body.get("organization", {}).get("id") or body["id"]


def cleanup_webhooks(sess: requests.Session) -> int:
    r = sess.get(f"{API}/admin/webhooks", timeout=10)
    if r.status_code != 200:
        return 0
    n = 0
    for w in r.json().get("webhooks", []):
        d = sess.delete(f"{API}/admin/webhooks/{w['id']}", timeout=10)
        if d.status_code in (200, 204):
            n += 1
    return n


# ===================================================================
print("[start]", flush=True)
print(f"[config] API={API} webhook_site={'yes' if WEBHOOK_TOKEN else 'no'} cron_secret={'yes' if CRON_SECRET else 'no'}", flush=True)

# Sanity: API up
r = requests.get(f"{API}/health", timeout=5)
assert r.status_code == 200, "API /health not responsive"

# Bootstrap: admin2 may have no membership on the live DB — repair if needed
# so cross-org tests have a real "different church" admin to use.
def _bootstrap_test_users():
    """Ensure seeded test users have the memberships the smoke tests assume.
    The live Render DB has only admin1's membership intact; everyone else lost
    theirs at some point. We restore: member1@test-church-1, member2@test-church-1,
    admin2@test-church-2 (creating that org if absent)."""
    sys.path.insert(0, ".")
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.membership import Membership
    from app.models.role import Role
    from app.models.organization import Organization
    db = SessionLocal()
    created = []
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        member_role = db.query(Role).filter(Role.name == "member").first()
        org1 = db.query(Organization).filter(Organization.key == "test-church-1").first()
        org2 = db.query(Organization).filter(Organization.key == "test-church-2").first()
        if not org2:
            org2 = Organization(
                name="Test Church 2", key="test-church-2",
                city="City 2", state="OH", country="USA",
                status="active", is_comped=True,
            )
            db.add(org2); db.flush()
            created.append(f"org test-church-2 ({org2.id})")

        plan = [
            ("admin2@test.com", org2, admin_role, True),
            ("member1@test.com", org1, member_role, False),
            ("member2@test.com", org1, member_role, False),
        ]
        for email, org, role, primary in plan:
            u = db.query(User).filter(User.email == email).first()
            if not u or not org or not role:
                continue
            existing = db.query(Membership).filter(Membership.user_id == u.id).first()
            if existing:
                continue
            m = Membership(
                user_id=u.id, organization_id=org.id, role_id=role.id,
                is_primary_admin=primary, status="active",
            )
            db.add(m)
            created.append(f"{email} -> {org.key} ({role.name})")
        db.commit()
        return created
    finally:
        db.close()

for line in _bootstrap_test_users():
    print(f"  [bootstrap] {line}", flush=True)

# Logins
print("[login]", flush=True)
sess_member = login("member1@test.com")
sess_admin = login("admin1@test.com")
sess_admin2 = login("admin2@test.com")  # Different church, for B9 cross-org
sess_master = login("master@test.com")
sess_user = login("user1@test.com")
print("  PASS  logged in as 5 seeded users", flush=True)

ORG1 = get_admin_org_id(sess_admin)
ORG2 = get_admin_org_id(sess_admin2)
print(f"  [orgs] org1={ORG1} org2={ORG2}", flush=True)

# Pre-clean any leftover webhooks from prior runs
cleanup_webhooks(sess_admin)
cleanup_webhooks(sess_admin2)

# ===================================================================
# Phase A — Notifications
# ===================================================================
print("[phase-A]", flush=True)

def t_a1_unread_count_endpoint():
    r = sess_admin.get(f"{API}/notifications/unread-count", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "count" in body and isinstance(body["count"], int), body
run("A1 GET /notifications/unread-count returns {count:int}", t_a1_unread_count_endpoint)

# Frontend poll cadence — read the source
def t_a1_poll_cadence():
    p = "../web/src/context/NotificationContext.tsx"
    text = open(p, encoding="utf-8").read()
    assert "60000" in text or "60 * 1000" in text, "poll constant != 60s in NotificationContext.tsx"
    assert "30000" not in text or "// 30s" in text, "still has 30000 — may be old poll value"
run("A1 NotificationContext poll constant == 60000", t_a1_poll_cadence)

def t_a3_mark_all_read_renamed():
    r = sess_admin.patch(f"{API}/notifications/mark-all-read", timeout=10)
    assert r.status_code == 200, r.status_code
    r2 = sess_admin.patch(f"{API}/notifications/read-all", timeout=10)
    assert r2.status_code in (404, 405), f"old route still present: {r2.status_code}"
run("A3 /mark-all-read works; /read-all is gone", t_a3_mark_all_read_renamed)

# Mark all read so we have a clean baseline for A2
sess_admin.patch(f"{API}/notifications/mark-all-read", timeout=10)
sess_admin2.patch(f"{API}/notifications/mark-all-read", timeout=10)
sess_master.patch(f"{API}/notifications/mark-all-read", timeout=10)

# A2 — member submits an assessment, admin gets notification
def t_a2_member_submit_notifies_admin():
    before = sess_admin.get(f"{API}/notifications", timeout=10).json()["unread_count"]
    submit_assessment(sess_member, "gps")
    time.sleep(1)
    after = sess_admin.get(f"{API}/notifications", timeout=10).json()
    assert after["unread_count"] > before, f"unread_count {before}->{after['unread_count']}"
    # Find the assessment_completed notification
    found = next(
        (n for n in after["notifications"] if n["type"] == "assessment_completed"),
        None,
    )
    assert found is not None, f"no assessment_completed in {[n['type'] for n in after['notifications'][:5]]}"
    assert "Bob" in found["title"] or "Wilson" in found["title"] or "Bob" in found["message"], found
run("A2 member GPS submit -> admin assessment_completed notification", t_a2_member_submit_notifies_admin)

# A4 — Boolean is_read is bool in the response (smoke_e2e covers DB; this is wire-shape)
def t_a4_is_read_is_bool():
    body = sess_admin.get(f"{API}/notifications", params={"limit": 5}, timeout=10).json()
    for n in body["notifications"]:
        assert isinstance(n["is_read"], bool), f"is_read not bool: {n!r}"
run("A4 /notifications response is_read is bool (not Y/N)", t_a4_is_read_is_bool)

# A5 — verify each event type can land on a notification record
# assessment_completed already covered by A2. Member self-completion:
def t_a5_self_completed_for_member():
    submit_assessment(sess_member, "myimpact")
    time.sleep(1)
    nots = sess_member.get(f"{API}/notifications", timeout=10).json()["notifications"]
    types = [n["type"] for n in nots[:10]]
    assert "assessment_self_completed" in types, f"types: {types}"
run("A5 member self-completion -> assessment_self_completed", t_a5_self_completed_for_member)

# member_joined + member_requested are tested in C4 (link-request flow)
# church_created tested in E4 (master add church)

# ===================================================================
# Phase B — Webhooks
# ===================================================================
print("[phase-B]", flush=True)

# B1 — Frontend component exists
def t_b1_panel_exists():
    p = "../web/src/components/CrmIntegrationPanel.tsx"
    assert os.path.exists(p), f"missing: {p}"
run("B1 CrmIntegrationPanel.tsx exists", t_b1_panel_exists)

# B5 — SSRF guard at the admin API
def t_b5_ssrf_localhost():
    r = sess_admin.post(f"{API}/admin/webhooks", json={
        "webhook_url": "http://localhost:8080/x",
        "event_type": "assessment_completed",
    }, timeout=10)
    assert r.status_code in (400, 422), r.status_code
    assert "private" in r.text.lower() or "loopback" in r.text.lower() or "localhost" in r.text.lower(), r.text[:200]
run("B5 POST localhost webhook -> 4xx with private-IP error", t_b5_ssrf_localhost)

def t_b5_ssrf_10x():
    r = sess_admin.post(f"{API}/admin/webhooks", json={
        "webhook_url": "http://10.0.0.1/x",
        "event_type": "assessment_completed",
    }, timeout=10)
    assert r.status_code in (400, 422), r.status_code
    assert "private" in r.text.lower(), r.text[:200]
run("B5 POST 10.x.x.x webhook -> 4xx with private-IP error", t_b5_ssrf_10x)

def t_b5_ssrf_file():
    r = sess_admin.post(f"{API}/admin/webhooks", json={
        "webhook_url": "file:///etc/passwd",
        "event_type": "assessment_completed",
    }, timeout=10)
    assert r.status_code in (400, 422), r.status_code
    assert "scheme" in r.text.lower() or "http" in r.text.lower(), r.text[:200]
run("B5 POST file:// webhook -> 4xx with scheme error", t_b5_ssrf_file)

# B7 — Cron secret enforcement
def t_b7_no_header():
    r = requests.post(f"{API}/internal/webhooks/process-retries", timeout=10)
    assert r.status_code == 404, r.status_code
run("B7 cron endpoint without secret -> 404", t_b7_no_header)

def t_b7_wrong_header():
    r = requests.post(
        f"{API}/internal/webhooks/process-retries",
        headers={"X-Internal-Secret": "wrong-secret-value"},
        timeout=10,
    )
    assert r.status_code == 404, r.status_code
run("B7 cron endpoint with wrong secret -> 404", t_b7_wrong_header)

if not CRON_SECRET:
    skip("B7 cron endpoint with right secret -> 200", "INTERNAL_CRON_SECRET not set in env")
else:
    def t_b7_correct_header():
        r = requests.post(
            f"{API}/internal/webhooks/process-retries",
            headers={"X-Internal-Secret": CRON_SECRET},
            timeout=10,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        body = r.json()
        assert "processed" in body and isinstance(body["processed"], int), body
    run("B7 cron endpoint with right secret -> 200 + {processed:int}", t_b7_correct_header)

# B2/B3/B4 — webhook.site round-trips (skip if no URL)
created_webhook_id = None
created_secret = None

if not WEBHOOK_TOKEN:
    skip("B2 create + test assessment webhook (signed)", "no WEBHOOK_SITE_URL")
    skip("B3 end-to-end real assessment payload", "no WEBHOOK_SITE_URL")
    skip("B4 end-to-end registration payload", "no WEBHOOK_SITE_URL")
else:
    webhook_site_clear()

    def t_b2_create_with_secret():
        global created_webhook_id, created_secret
        r = sess_admin.post(f"{API}/admin/webhooks", json={
            "webhook_url": WEBHOOK_SITE_URL,
            "event_type": "assessment_completed",
            "is_active": True,
            "generate_secret": True,
        }, timeout=10)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("secret_plaintext"), "secret_plaintext missing on create"
        created_webhook_id = body["id"]
        created_secret = body["secret_plaintext"]
    run("B2 POST /admin/webhooks generate_secret -> secret_plaintext returned once", t_b2_create_with_secret)

    def t_b2_get_returns_masked():
        r = sess_admin.get(f"{API}/admin/webhooks/{created_webhook_id}", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body.get("secret_masked", "").startswith("••••"), body
        assert body.get("secret_plaintext") in (None, ""), "secret leaked on GET"
    run("B2 GET /admin/webhooks/{id} -> secret masked, plaintext absent", t_b2_get_returns_masked)

    def t_b2_test_synchronous():
        r = sess_admin.post(f"{API}/admin/webhooks/{created_webhook_id}/test", timeout=15)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        body = r.json()
        assert body["ok"] is True, body
        assert body["status_code"] == 200, body
    run("B2 POST /admin/webhooks/{id}/test -> ok=true, 200", t_b2_test_synchronous)

    def t_b2_inbox_received_test():
        req = webhook_site_wait(
            lambda r: r.get("headers", {}).get("x-gps-event") == ["assessment_completed"]
            and r.get("method") == "POST"
            and '"test"' in (r.get("content") or ""),
            timeout=15,
        )
        assert req is not None, "test webhook never arrived at webhook.site"
        # signature check
        sig_header = req["headers"].get("x-gps-signature", [None])[0]
        assert sig_header and sig_header.startswith("sha256="), f"signature header: {sig_header}"
        body_bytes = (req.get("content") or "").encode("utf-8")
        expected = "sha256=" + hmac.new(created_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        assert hmac.compare_digest(sig_header, expected), f"sig mismatch:\n got {sig_header}\n want {expected}"
        body_obj = json.loads(req["content"])
        assert body_obj.get("test") is True, body_obj
    run("B2 webhook.site received signed test payload (HMAC matches)", t_b2_inbox_received_test)

    def t_b3_real_assessment_delivers():
        webhook_site_clear()
        time.sleep(1)
        submit_assessment(sess_member, "gps")
        req = webhook_site_wait(
            lambda r: r.get("headers", {}).get("x-gps-event") == ["assessment_completed"]
            and '"test": true' not in (r.get("content") or "")
            and '"test":true' not in (r.get("content") or ""),
            timeout=20,
        )
        assert req is not None, "real assessment payload didn't reach webhook.site"
        body_obj = json.loads(req["content"])
        # Real payload should not have test=True and should have user data
        assert body_obj.get("test") is not True, body_obj
        assert "user" in body_obj or "userEmail" in body_obj or "email" in str(body_obj).lower()
    run("B3 real assessment submit -> webhook.site receives non-test payload", t_b3_real_assessment_delivers)

    def t_b3_delivery_log_success():
        r = sess_admin.get(f"{API}/admin/webhooks/{created_webhook_id}/deliveries", timeout=10)
        assert r.status_code == 200
        deliveries = r.json()["deliveries"]
        success = [d for d in deliveries if d["status"] == "success"]
        assert len(success) >= 1, [d["status"] for d in deliveries[:5]]
        assert success[0]["http_status_code"] == 200
        assert success[0]["attempts"] == 1
    run("B3 GET /deliveries shows status=success, attempts=1", t_b3_delivery_log_success)

# ---- B4: registration webhook
reg_webhook_id = None
b4_user_email = None

if not WEBHOOK_TOKEN:
    skip("B4 user_registered webhook fires on org-key registration", "no WEBHOOK_SITE_URL")
else:
    def t_b4_create_reg_webhook():
        global reg_webhook_id
        r = sess_admin.post(f"{API}/admin/webhooks", json={
            "webhook_url": WEBHOOK_SITE_URL,
            "event_type": "user_registered",
            "is_active": True,
        }, timeout=10)
        assert r.status_code in (200, 201), r.text[:200]
        reg_webhook_id = r.json()["id"]
    run("B4 create user_registered webhook config", t_b4_create_reg_webhook)

    def t_b4_register_with_org_key_fires():
        global b4_user_email
        webhook_site_clear()
        time.sleep(1)
        suffix = uuid.uuid4().hex[:8]
        b4_user_email = f"smoke-b4-{suffix}@example.com"
        r = requests.post(f"{API}/auth/register", json={
            "email": b4_user_email,
            "password": "TestPass#2024",
            "first_name": "Smoke",
            "last_name": f"B4-{suffix}",
            "organization_key": "test-church-1",
        }, timeout=15)
        assert r.status_code in (200, 201), f"register: {r.status_code} {r.text[:200]}"
        req = webhook_site_wait(
            lambda r: r.get("headers", {}).get("x-gps-event") == ["user_registered"],
            timeout=20,
        )
        assert req is not None, "user_registered never arrived"
        body = json.loads(req["content"])
        assert body.get("test") is not True, body
        # Either email at root or under user
        as_str = json.dumps(body)
        assert b4_user_email in as_str, f"new-user email not in payload: {as_str[:300]}"
    run("B4 register with org_key -> user_registered webhook delivered", t_b4_register_with_org_key_fires)

# B6 — retry-on-failure (single failed attempt + cron-trigger redelivery)
fail_webhook_id = None

def t_b6_failed_delivery_recorded():
    global fail_webhook_id
    # Need to remove the existing assessment_completed config first
    r = sess_admin.get(f"{API}/admin/webhooks", timeout=10)
    for w in r.json().get("webhooks", []):
        if w["event_type"] == "assessment_completed":
            sess_admin.delete(f"{API}/admin/webhooks/{w['id']}", timeout=10)
    # Now create one pointing at httpbin/status/500
    r = sess_admin.post(f"{API}/admin/webhooks", json={
        "webhook_url": "https://httpbin.org/status/500",
        "event_type": "assessment_completed",
    }, timeout=10)
    assert r.status_code in (200, 201), r.text[:200]
    fail_webhook_id = r.json()["id"]
    # Fire by submitting an assessment
    submit_assessment(sess_member, "gps")
    time.sleep(2)
    deliveries = sess_admin.get(f"{API}/admin/webhooks/{fail_webhook_id}/deliveries", timeout=10).json()["deliveries"]
    failed = [d for d in deliveries if d["status"] == "failed"]
    assert len(failed) >= 1, [d["status"] for d in deliveries[:5]]
    assert failed[0]["attempts"] == 1
    assert failed[0]["next_retry_at"] is not None
run("B6 failed webhook -> status=failed, attempts=1, next_retry_at scheduled", t_b6_failed_delivery_recorded)

if not CRON_SECRET:
    skip("B6 cron-triggered retry redelivers", "INTERNAL_CRON_SECRET not set")
else:
    def t_b6_cron_processes_retry():
        # next_retry_at is ~60s out. Poll the cron endpoint.
        # First call should return processed=0 (still too early).
        r = requests.post(
            f"{API}/internal/webhooks/process-retries",
            headers={"X-Internal-Secret": CRON_SECRET},
            timeout=10,
        )
        assert r.status_code == 200
        immediate = r.json()["processed"]
        # Wait for next_retry_at to elapse.
        deadline = time.time() + 90
        eventual = 0
        while time.time() < deadline:
            time.sleep(10)
            r2 = requests.post(
                f"{API}/internal/webhooks/process-retries",
                headers={"X-Internal-Secret": CRON_SECRET},
                timeout=15,
            )
            if r2.status_code == 200 and r2.json().get("processed", 0) > 0:
                eventual = r2.json()["processed"]
                break
        assert eventual >= 1, f"cron never processed retry within 90s (immediate={immediate})"
        # Verify delivery row now shows attempts=2
        deliveries = sess_admin.get(f"{API}/admin/webhooks/{fail_webhook_id}/deliveries", timeout=10).json()["deliveries"]
        max_attempts = max((d["attempts"] for d in deliveries), default=0)
        assert max_attempts >= 2, [d["attempts"] for d in deliveries[:5]]
    run("B6 cron processes due retry -> attempts increments to 2", t_b6_cron_processes_retry)

# B8 — Master read-only view
def t_b8_master_sees_org_webhooks():
    # Ensure there's at least one long-URL webhook so masking can be observed.
    long_url = WEBHOOK_SITE_URL or "https://hooks.zapier.com/hooks/catch/12345678/abcdefghij/"
    # Ensure a fresh assessment_completed config exists pointing at the long URL.
    for w in sess_admin.get(f"{API}/admin/webhooks", timeout=10).json().get("webhooks", []):
        if w["event_type"] == "assessment_completed":
            sess_admin.delete(f"{API}/admin/webhooks/{w['id']}", timeout=10)
    sess_admin.post(f"{API}/admin/webhooks", json={
        "webhook_url": long_url,
        "event_type": "assessment_completed",
        "generate_secret": True,
    }, timeout=10)
    r = sess_master.get(f"{API}/master/organizations/{ORG1}/webhooks", timeout=10)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    body = r.json()
    webhooks = body.get("webhooks", [])
    assert len(webhooks) >= 1, f"master should see >=1 webhook for org1; got: {body}"
    for w in webhooks:
        assert "secret_plaintext" not in w, "master leaked secret_plaintext"
        assert "secret" not in w, f"master leaked raw secret: {w}"
        masked = w.get("webhook_url_masked", "")
        if w["webhook_url_masked"] and len(long_url) > 36 and w.get("event_type") == "assessment_completed":
            assert "…" in masked or "•" in masked, f"long url not masked: {masked}"
run("B8 master GET /master/organizations/{org}/webhooks -> masked, no secret", t_b8_master_sees_org_webhooks)

# B9 — cross-org access blocked
def t_b9_cross_org_404():
    # admin1 has the webhook config; admin2 (different church) tries to read it
    org1_webhooks = sess_admin.get(f"{API}/admin/webhooks", timeout=10).json()["webhooks"]
    assert len(org1_webhooks) >= 1
    target_id = org1_webhooks[0]["id"]
    r = sess_admin2.get(f"{API}/admin/webhooks/{target_id}", timeout=10)
    assert r.status_code == 404, f"expected 404, got {r.status_code}"
run("B9 admin of Church B GETs Church A webhook -> 404", t_b9_cross_org_404)

# ===================================================================
# Phase C — Event wiring
# ===================================================================
print("[phase-C]", flush=True)

# C1 — broken URL doesn't crash assessment submit
def t_c1_broken_url_assessment_still_200():
    # Replace assessment_completed config with a non-resolving host
    for w in sess_admin.get(f"{API}/admin/webhooks", timeout=10).json()["webhooks"]:
        if w["event_type"] == "assessment_completed":
            sess_admin.delete(f"{API}/admin/webhooks/{w['id']}", timeout=10)
    r = sess_admin.post(f"{API}/admin/webhooks", json={
        "webhook_url": "https://does-not-exist-12345.example.com/hook",
        "event_type": "assessment_completed",
    }, timeout=10)
    assert r.status_code in (200, 201), r.text[:200]
    broken_id = r.json()["id"]
    # Submit assessment — should still succeed
    res = submit_assessment(sess_member, "gps")
    assert res["assessment_id"]
    time.sleep(2)
    deliveries = sess_admin.get(f"{API}/admin/webhooks/{broken_id}/deliveries", timeout=10).json()["deliveries"]
    failed = [d for d in deliveries if d["status"] == "failed"]
    assert len(failed) >= 1
    assert failed[0]["error_message"] is not None
    sess_admin.delete(f"{API}/admin/webhooks/{broken_id}", timeout=10)
run("C1 broken webhook URL -> assessment still 200, delivery=failed w/ error_message", t_c1_broken_url_assessment_still_200)

# C2 — independent registration (no org_key) does not fire user_registered
c2_email = f"smoke-c2-{uuid.uuid4().hex[:8]}@example.com"

def t_c2_independent_reg_no_webhook():
    if WEBHOOK_TOKEN:
        webhook_site_clear()
        time.sleep(1)
    r = requests.post(f"{API}/auth/register", json={
        "email": c2_email,
        "password": "TestPass#2024",
        "first_name": "Smoke", "last_name": "C2",
    }, timeout=15)
    assert r.status_code in (200, 201), r.text[:200]
    if WEBHOOK_TOKEN:
        time.sleep(4)  # short delay to let any webhook arrive
        # Look for the c2 email in any inbox request
        inbox = requests.get(WEBHOOK_INSPECT, params={"sorting": "newest"}, timeout=10).json().get("data", [])
        for req in inbox:
            assert c2_email not in (req.get("content") or ""), "saw user_registered for independent reg"
run("C2 register without org_key -> no user_registered webhook", t_c2_independent_reg_no_webhook)

# C3 — Notifications work even with no webhooks configured
def t_c3_notifications_independent_of_webhooks():
    # Delete all webhooks for org1
    for w in sess_admin.get(f"{API}/admin/webhooks", timeout=10).json()["webhooks"]:
        sess_admin.delete(f"{API}/admin/webhooks/{w['id']}", timeout=10)
    sess_admin.patch(f"{API}/notifications/mark-all-read", timeout=10)
    submit_assessment(sess_member, "gps")
    time.sleep(1)
    nots = sess_admin.get(f"{API}/notifications", timeout=10).json()["notifications"]
    assert any(n["type"] == "assessment_completed" for n in nots[:5]), [n["type"] for n in nots[:5]]
run("C3 no webhooks -> assessment_completed notification still fires", t_c3_notifications_independent_of_webhooks)

# C4 — link-request -> member_requested notification, then approval -> member_joined
# Use the seeded user1@test.com (verified, no membership) to avoid the
# email_not_verified gate on /dashboard/link-request.
c4_user_email = "user1@test.com"

def _ensure_user1_unaffiliated():
    """Remove any leftover memberships on user1 from prior test runs."""
    sys.path.insert(0, ".")
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.membership import Membership
    from app.models.notification import Notification
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == c4_user_email).first()
        if u:
            db.query(Membership).filter(Membership.user_id == u.id).delete()
            # Also clear stale notifications so they don't pollute admin's bell
            db.commit()
    finally:
        db.close()

def t_c4_link_request_and_approve():
    _ensure_user1_unaffiliated()
    sess_c4 = login(c4_user_email)
    sess_admin.patch(f"{API}/notifications/mark-all-read", timeout=10)
    r = sess_c4.post(f"{API}/dashboard/link-request", json={
        "organization_id": ORG1,
        "message": "Smoke test link request",
    }, timeout=10)
    assert r.status_code in (200, 201), f"link-request: {r.status_code} {r.text[:200]}"
    time.sleep(1)
    nots = sess_admin.get(f"{API}/notifications", timeout=10).json()["notifications"]
    assert any(n["type"] == "member_requested" for n in nots[:5]), [n["type"] for n in nots[:5]]
    # Find the pending membership_id
    pending = sess_admin.get(f"{API}/admin/pending", timeout=10).json()
    items = pending if isinstance(pending, list) else pending.get("pending", pending.get("items", []))
    me_pending = None
    for p in items:
        if p.get("user", {}).get("email") == c4_user_email or p.get("email") == c4_user_email:
            me_pending = p
            break
    assert me_pending, f"didn't find pending for {c4_user_email}: {[i.get('user',{}).get('email') for i in items[:5]]}"
    membership_id = me_pending.get("id") or me_pending.get("membership_id")
    sess_admin.patch(f"{API}/notifications/mark-all-read", timeout=10)
    if WEBHOOK_TOKEN:
        # Re-create user_registered webhook so we can verify it fires on approval
        for w in sess_admin.get(f"{API}/admin/webhooks", timeout=10).json()["webhooks"]:
            if w["event_type"] == "user_registered":
                sess_admin.delete(f"{API}/admin/webhooks/{w['id']}", timeout=10)
        sess_admin.post(f"{API}/admin/webhooks", json={
            "webhook_url": WEBHOOK_SITE_URL,
            "event_type": "user_registered",
        }, timeout=10)
        webhook_site_clear()
        time.sleep(1)
    r = sess_admin.post(f"{API}/admin/pending/{membership_id}/approve", timeout=10)
    assert r.status_code in (200, 201, 204), f"approve: {r.status_code} {r.text[:200]}"
    time.sleep(2)
    nots = sess_admin.get(f"{API}/notifications", timeout=10).json()["notifications"]
    assert any(n["type"] == "member_joined" for n in nots[:5]), [n["type"] for n in nots[:5]]
    if WEBHOOK_TOKEN:
        req = webhook_site_wait(
            lambda r: r.get("headers", {}).get("x-gps-event") == ["user_registered"]
                       and c4_user_email in (r.get("content") or ""),
            timeout=20,
        )
        assert req is not None, "user_registered webhook never fired on approval"
run("C4 link-request + approve -> member_requested then member_joined + user_registered", t_c4_link_request_and_approve)

# C5 — church_created — needs second master, skip-with-note
skip("C5 church_created notification fires to other masters", "only one master in seed (master@test.com)")

# ===================================================================
# Phase D — Spanish
# ===================================================================
print("[phase-D]", flush=True)

# D1 — locale toggle via API
def t_d1_set_locale_es():
    r = sess_member.put(f"{API}/auth/profile", json={"locale": "es"}, timeout=10)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    assert r.json()["locale"] == "es"
run("D1 PUT /auth/profile locale=es -> 200", t_d1_set_locale_es)

# D2 — persists across sessions (re-login)
def t_d2_locale_persists():
    fresh = login("member1@test.com")
    body = me(fresh)
    assert body["locale"] == "es", body
run("D2 locale persists across re-login", t_d2_locale_persists)

# D3 — locale validation rejects garbage
def t_d3_locale_fr_rejected():
    r = sess_member.put(f"{API}/auth/profile", json={"locale": "fr"}, timeout=10)
    assert r.status_code == 422, r.status_code
run("D3 locale=fr -> 422", t_d3_locale_fr_rejected)

def t_d3_locale_zh_rejected():
    r = sess_member.put(f"{API}/auth/profile", json={"locale": "ZH-cn"}, timeout=10)
    assert r.status_code == 422, r.status_code
run("D3 locale=ZH-cn -> 422", t_d3_locale_zh_rejected)

# D4 — Spanish GPS questions exist
def t_d4_gps_spanish():
    form = fetch_questions(sess_member, "gps")
    es = [q.get("question_es") for q in form["questions"] if q.get("question_es")]
    assert len(es) >= 50, f"only {len(es)} GPS questions have question_es"
    assert any("Busco" in q or "Dios" in q or "Cristo" in q for q in es), "no recognizable Spanish text"
run("D4 GPS questions have question_es populated", t_d4_gps_spanish)

# D5 — Spanish MyImpact questions exist (smoke_live verified count; this checks API)
def t_d5_myimpact_spanish():
    form = fetch_questions(sess_member, "myimpact")
    es = [q.get("question_es") for q in form["questions"] if q.get("question_es")]
    assert len(es) >= 15, f"only {len(es)} MyImpact questions have question_es"
    assert any("amorosa" in q.lower() or "soy una persona" in q.lower() for q in es), "no recognizable Spanish text"
run("D5 MyImpact questions have question_es populated", t_d5_myimpact_spanish)

# D6 — gifts_passions.description_es field present in GPS results
def t_d6_results_has_description_es_field():
    # Submit a GPS assessment to get a result
    res = submit_assessment(sess_member, "gps")
    body = res["result"]
    # Find a gift in the results (shape varies; just stringify and look for the field name)
    s = json.dumps(body)
    assert "description_es" in s or "descriptionEs" in s, "description_es field missing from results payload"
run("D6 GPS results include description_es field on gifts (may be NULL)", t_d6_results_has_description_es_field)

# Reset locale back to en for cleanup-friendly state
sess_member.put(f"{API}/auth/profile", json={"locale": "en"}, timeout=10)

# ===================================================================
# Phase E — included items
# ===================================================================
print("[phase-E]", flush=True)

def t_e1_help_link_exists():
    p = "../web/src/components/HelpLink.tsx"
    assert os.path.exists(p), p
    text = open(p, encoding="utf-8").read()
    assert "info@disciplesmade.com" in text or "mailto:" in text, "expected mailto in HelpLink"
run("E1 HelpLink.tsx exists with mailto", t_e1_help_link_exists)

def t_e2_billing_portal_endpoint():
    r = sess_admin.post(f"{API}/billing/portal", timeout=15)
    # Either 200 with a stripe URL, or a Stripe config error if no subscription, or 4xx if no active subscription
    assert r.status_code in (200, 400, 404, 503), f"unexpected: {r.status_code} {r.text[:200]}"
    if r.status_code == 200:
        body = r.json()
        url = body.get("url") or body.get("portal_url") or ""
        assert "stripe.com" in url or "billing.stripe" in url, body
run("E2 POST /billing/portal as primary admin -> 200/4xx (no live subscription guaranteed)", t_e2_billing_portal_endpoint)

def t_e3_impersonation_blocks_billing_portal():
    # Master impersonates admin1
    me_admin = me(sess_admin)
    r = sess_master.post(f"{API}/master/impersonate", json={
        "user_id": me_admin["id"],
        "reason": "smoke test",
    }, timeout=10)
    if r.status_code == 500 and "parameter `request`" in r.text:
        # Pre-existing slowapi/FastAPI parameter-name collision in
        # api/app/routers/master.py:728 — handler param is named `request`
        # which shadows what slowapi expects to be a Starlette Request.
        # This BUG predates the addendum work; flag separately.
        raise AssertionError(
            "BUG: /master/impersonate returns 500 due to slowapi naming "
            "collision in master.py:728 (rename `request: ImpersonateRequest`). "
            "E3 cannot be exercised end-to-end until that's fixed."
        )
    assert r.status_code in (200, 201), f"impersonate: {r.status_code} {r.text[:200]}"
    imp_token = r.json()["access_token"]
    s_imp = requests.Session()
    s_imp.headers["Authorization"] = f"Bearer {imp_token}"
    r2 = s_imp.post(f"{API}/billing/portal", timeout=15)
    assert r2.status_code == 403, f"expected 403, got {r2.status_code} {r2.text[:200]}"
run("E3 impersonator hitting /billing/portal -> 403", t_e3_impersonation_blocks_billing_portal)

added_church_id = None
def t_e4_master_add_church():
    global added_church_id
    suffix = uuid.uuid4().hex[:8]
    body = {
        "name": f"SmokeTest Church E4 {suffix}",
        "city": "TestCity",
        "state": "OH",
        "country": "USA",
        "primary_admin_email": f"smoke-e4-{suffix}@example.com",
        "primary_admin_first_name": "Smoke",
        "primary_admin_last_name": f"E4-{suffix}",
    }
    r = sess_master.post(f"{API}/master/churches", json=body, timeout=15)
    assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"
    out = r.json()
    added_church_id = out.get("id") or out.get("church_id")
    assert added_church_id, out
    assert out.get("key", "").startswith("smoketest-church"), out.get("key")
    # Audit log entry
    audit = sess_master.get(f"{API}/master/audit-log", timeout=10).json()
    items = audit if isinstance(audit, list) else audit.get("entries", audit.get("items", []))
    assert any(e.get("action") == "master_create_church" for e in items[:20]), [e.get("action") for e in items[:5]]
run("E4 master POST /master/churches -> 201 + audit log master_create_church", t_e4_master_add_church)

# ===================================================================
# Cleanup
# ===================================================================
print("[cleanup]", flush=True)

def safe(fn, *a, **kw):
    try: return fn(*a, **kw)
    except Exception as e: print(f"  cleanup warn: {e}")

# Webhooks
n_w = cleanup_webhooks(sess_admin) + cleanup_webhooks(sess_admin2)
print(f"  removed {n_w} webhook configs")

# Reset locale
safe(sess_member.put, f"{API}/auth/profile", json={"locale": "en"}, timeout=10)

# Delete transient users via SQL (no admin endpoint for arbitrary user delete)
try:
    sys.path.insert(0, ".")
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.membership import Membership
    from app.models.notification import Notification
    from app.models.organization import Organization
    db = SessionLocal()
    transient_emails = [e for e in [b4_user_email, c2_email] if e]
    u1 = db.query(User).filter(User.email == "user1@test.com").first()
    if u1:
        db.query(Membership).filter(Membership.user_id == u1.id).delete()

    def _purge_user(u):
        if not u: return
        # Tables that hold FKs to users — clear before deleting.
        for tbl in ("password_reset_tokens", "audit_log", "email_verification_tokens", "answers", "assessments"):
            try:
                db.execute(text(f"DELETE FROM {tbl} WHERE user_id = :uid"), {"uid": str(u.id)})
            except Exception:
                pass
        db.query(Notification).filter(Notification.user_id == u.id).delete()
        db.query(Membership).filter(Membership.user_id == u.id).delete()
        db.delete(u)

    for em in transient_emails:
        _purge_user(db.query(User).filter(User.email == em).first())

    if added_church_id:
        org = db.query(Organization).filter(Organization.id == uuid.UUID(added_church_id)).first()
        if org:
            mems = db.query(Membership).filter(Membership.organization_id == org.id).all()
            user_ids = [m.user_id for m in mems]
            db.query(Notification).filter(Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(Membership).filter(Membership.organization_id == org.id).delete()
            for uid in user_ids:
                u = db.query(User).filter(User.id == uid).first()
                if u and u.email and u.email.startswith("smoke-e4-"):
                    _purge_user(u)
            db.delete(org)
    db.commit()
    db.close()
    print(f"  cleaned up {len(transient_emails)} transient users + test church")
except Exception as e:
    print(f"  cleanup error (non-fatal): {e}")

# ===================================================================
print(f"\n[summary] PASS={PASS} FAIL={FAIL} SKIP={SKIP}", flush=True)
sys.exit(0 if FAIL == 0 else 1)
