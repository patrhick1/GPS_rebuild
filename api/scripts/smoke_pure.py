"""Smoke tests — pure (no DB, no network)."""
print("[start]", flush=True)
import sys, os, hashlib, hmac, traceback, uuid
from datetime import datetime, timezone
sys.path.insert(0, ".")

# Avoid loading .env (which would trigger DATABASE_URL resolution).
# Pure tests don't need it.
os.environ.setdefault("DATABASE_URL", "postgresql://x@x/x")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import pydantic
from app.schemas.user import UserUpdate
from app.services.webhook_payloads import (
    build_assessment_payload,
    build_test_assessment_payload,
    build_user_registered_payload,
)
from app.services.webhook_service import (
    BACKOFF_SECONDS, MAX_ATTEMPTS, assert_url_safe,
)

PASS = 0
FAIL = 0


def assert_(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def check(name, ok, msg=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS  {name}", flush=True)
    else:
        FAIL += 1
        print(f"  FAIL  {name}: {msg}", flush=True)


def run(name, fn):
    try:
        fn()
        check(name, True)
    except AssertionError as e:
        check(name, False, str(e))
    except Exception:
        check(name, False, traceback.format_exc().splitlines()[-1])


# -------- locale validation
print("[locale]", flush=True)

run("UserUpdate(locale='es')", lambda: assert_(UserUpdate(locale="es").locale == "es"))
run("UserUpdate(locale='en')", lambda: assert_(UserUpdate(locale="en").locale == "en"))
run("UserUpdate(locale=None)", lambda: assert_(UserUpdate(locale=None).locale is None))


def reject_locale(v):
    try:
        UserUpdate(locale=v)
        raise AssertionError(f"Expected ValidationError for {v!r}")
    except pydantic.ValidationError:
        pass


run("UserUpdate(locale='fr') rejected", lambda: reject_locale("fr"))
run("UserUpdate(locale='ZH-cn') rejected", lambda: reject_locale("ZH-cn"))


# -------- payload builders
print("[payloads]", flush=True)


class _U:
    id = uuid.UUID(int=1); first_name="Jane"; last_name="Smith"
    email="jane@example.com"; phone_number="555-1234"


class _O:
    id = uuid.UUID(int=2); name="Grace"; key="grace"


class _A:
    id = uuid.UUID(int=99); instrument_type="gps"
    completed_at = datetime(2026,5,1,12,0,0,tzinfo=timezone.utc)


class _G:
    def __init__(self, n, c, d):
        self.id=uuid.uuid4(); self.name=n; self.short_code=c; self.description=d


class _R:
    def __init__(self, gifts):
        ids=list(gifts.keys())
        self.gift_1_id=ids[0] if ids else None
        self.gift_2_id=ids[1] if len(ids)>1 else None
        self.gift_3_id=None; self.gift_4_id=None
        self.spiritual_gift_1_score=20; self.spiritual_gift_2_score=15
        self.spiritual_gift_3_score=None; self.spiritual_gift_4_score=None
        self.passion_1_id=None; self.passion_2_id=None; self.passion_3_id=None
        self.passion_1_score=None; self.passion_2_score=None; self.passion_3_score=None
        self.abilities="Project management, Web Development"
        self.people="Singles"; self.cause="Education"


def t_user_registered():
    p = build_user_registered_payload(user=_U(), organization=_O(), registered_at=datetime.now(timezone.utc))
    assert set(p.keys()) == {"event","user","church","registeredAt"}, p.keys()
    assert p["event"] == "user_registered"
    assert p["user"]["phone"] == "555-1234"
    assert p["church"]["key"] == "grace"


def t_gps_payload():
    g1=_G("Wisdom","W","desc"); g2=_G("Faith","F","desc")
    by_id={g1.id:g1, g2.id:g2}
    p = build_assessment_payload(assessment=_A(), user=_U(), organization=_O(),
                                 result=_R(by_id), gifts_by_id=by_id, story_questions=[])
    assert p["assessment"]["instrument"] == "gps"
    assert len(p["assessment"]["gifts"]) == 2
    assert p["assessment"]["abilities"] == ["Project management","Web Development"]


def t_myimpact_payload():
    class A: id=uuid.uuid4(); instrument_type="myimpact"; completed_at=datetime.now(timezone.utc)
    class M:
        character_score=7.5; calling_score=4.0; myimpact_score=30.0
        def get_character_breakdown(self): return {"loving":8}
        def get_calling_breakdown(self): return {"know_gifts":5}
    p = build_assessment_payload(assessment=A(), user=_U(), organization=_O(), myimpact_result=M())
    assert p["assessment"]["instrument"] == "myimpact"
    assert p["assessment"]["myImpactScores"]["character"] == 7.5


def t_test_payload_assessment():
    p = build_test_assessment_payload(event_type="assessment_completed")
    assert p["test"] is True
    assert p["user"]["firstName"] == "Test"


def t_test_payload_user_reg():
    p = build_test_assessment_payload(event_type="user_registered")
    assert p["test"] is True
    assert p["event"] == "user_registered"


run("user_registered payload shape", t_user_registered)
run("GPS payload shape", t_gps_payload)
run("MyImpact payload shape", t_myimpact_payload)
run("test payload (assessment)", t_test_payload_assessment)
run("test payload (user_registered)", t_test_payload_user_reg)


# -------- SSRF guard
print("[ssrf]", flush=True)


def reject(url):
    try:
        assert_url_safe(url)
        raise AssertionError(f"Expected ValueError for {url}")
    except ValueError:
        pass


run("https public accepted", lambda: assert_url_safe("https://webhook.site/abc") or True)
run("http://localhost rejected", lambda: reject("http://localhost:8080/x"))
run("http://127.0.0.1 rejected", lambda: reject("http://127.0.0.1/x"))
run("http://10.0.0.1 rejected", lambda: reject("http://10.0.0.1/x"))
run("http://192.168.1.1 rejected", lambda: reject("http://192.168.1.1/x"))
run("http://169.254.169.254 rejected", lambda: reject("http://169.254.169.254/x"))
run("file:// rejected", lambda: reject("file:///etc/passwd"))


# -------- HMAC + backoff
print("[hmac+backoff]", flush=True)


def t_hmac():
    secret = "test-secret-abc"; body = b'{"event":"x"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    sig2 = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sig == sig2 and len(sig) == 64


run("HMAC-SHA256 deterministic", t_hmac)
run("MAX_ATTEMPTS == 3", lambda: assert_(MAX_ATTEMPTS == 3))
run("backoff[1]==60", lambda: assert_(BACKOFF_SECONDS[1] == 60))
run("backoff[2]==300", lambda: assert_(BACKOFF_SECONDS[2] == 300))
run("backoff[3] absent", lambda: assert_(3 not in BACKOFF_SECONDS))


print(f"\n[summary] PASS={PASS} FAIL={FAIL}", flush=True)
sys.exit(0 if FAIL == 0 else 1)
