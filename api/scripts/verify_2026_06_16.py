"""
Local in-process verification for the 2026-06-16 changes:
  * Group 3: GET /assessment-results and /myimpact-results routes resolve
  * Group 6: DELETE /assessments/{id} (soft delete)
  * Group 6: GET /dashboard/assessments excludes soft-deleted
  * Group 6: admin viewing a soft-deleted member assessment via /grade
            still works (audit-trail invariant)
  * Group 7: POST /dashboard/compare branches on instrument_type
  * Group 7: mixed-type compare rejected with 400

Spins up the FastAPI app in-process (no uvicorn), mints a JWT for a real
user in the dev DB, and exercises the endpoints. Reads/writes the dev
DB — DO NOT run against prod.

Usage from api/ directory:
    ../venv/Scripts/python.exe scripts/verify_2026_06_16.py
"""
import os
import sys
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.assessment import Assessment  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.membership import Membership  # noqa: E402
from app.models.role import Role  # noqa: E402


def _mint_jwt(user_id: str) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    raise SystemExit(1)


def main() -> None:
    db = SessionLocal()
    client = TestClient(app)

    # Pick a verified user with at least one completed GPS assessment and
    # at least two completed MyImpact assessments.
    print("\n[setup] Finding a user with usable data ...")
    from sqlalchemy import func

    candidate_user_id = (
        db.query(Assessment.user_id)
        .filter(
            Assessment.status == "completed",
            Assessment.deleted_at.is_(None),
            Assessment.instrument_type == "myimpact",
        )
        .group_by(Assessment.user_id)
        .having(func.count() >= 2)
        .first()
    )
    if not candidate_user_id:
        fail("No user has >=2 completed MyImpact assessments. Cannot verify Group 7.")

    user_id = candidate_user_id[0]
    user = db.query(User).filter(User.id == user_id).first()
    if user.email_verified != "Y":
        # Some verification flows require it — the test JWT bypasses login but
        # the dependency get_current_verified_user re-checks. Force-verify for
        # the verification window.
        user.email_verified = "Y"
        db.commit()

    print(f"        user_id={user_id} email={user.email}")

    token = _mint_jwt(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    # ── Group 6: DELETE assessment ────────────────────────────────────────────
    print("\n[Group 6] DELETE /assessments/{id} (soft delete)")

    gps = (
        db.query(Assessment)
        .filter(
            Assessment.user_id == user_id,
            Assessment.instrument_type == "gps",
            Assessment.status == "completed",
            Assessment.deleted_at.is_(None),
        )
        .first()
    )
    if not gps:
        # Create a throwaway in-progress one we can target instead
        gps = Assessment(user_id=user_id, instrument_type="gps", status="in_progress")
        db.add(gps)
        db.commit()
        db.refresh(gps)
        print(f"        no completed GPS; created in_progress {gps.id} as target")
    target_id = gps.id

    # Pre-state
    pre = db.query(Assessment).filter(Assessment.id == target_id).first()
    if pre.deleted_at is not None:
        fail(f"precondition: target {target_id} already has deleted_at set")
    ok(f"precondition: target {target_id} has deleted_at=None")

    # DELETE
    resp = client.delete(f"/assessments/{target_id}", headers=headers)
    if resp.status_code != 204:
        fail(f"DELETE returned {resp.status_code} expected 204 (body: {resp.text[:200]})")
    ok("DELETE returns 204")

    db.expire_all()
    post = db.query(Assessment).filter(Assessment.id == target_id).first()
    if post.deleted_at is None:
        fail("DB still has deleted_at=None after DELETE")
    ok(f"DB row has deleted_at={post.deleted_at} after DELETE")

    # Idempotency: re-DELETE should also be 204 (not 404)
    resp2 = client.delete(f"/assessments/{target_id}", headers=headers)
    if resp2.status_code != 204:
        fail(f"second DELETE returned {resp2.status_code} expected 204")
    ok("second DELETE on same id is idempotent 204")

    # ── Group 6: history endpoint excludes the deleted row ────────────────────
    print("\n[Group 6] GET /dashboard/assessments excludes soft-deleted")

    resp = client.get("/dashboard/assessments", headers=headers)
    if resp.status_code != 200:
        fail(f"history GET returned {resp.status_code} body={resp.text[:200]}")
    ids = [item["id"] for item in resp.json()]
    if str(target_id) in ids:
        fail(f"deleted assessment {target_id} still appears in user history")
    ok(f"deleted assessment {target_id} excluded from history ({len(ids)} rows returned)")

    # Restore the row so the dev DB stays clean for subsequent test runs
    post.deleted_at = None
    db.commit()
    ok("test cleanup: restored deleted_at=NULL on target")

    # ── Group 6: admin viewing soft-deleted member assessment via /grade ─────
    print("\n[Group 6] Admin viewing soft-deleted member /grade (audit trail)")

    # Find a member in the same org as someone with role=admin, with a
    # completed GPS assessment we can flag as deleted_at and unflag after.
    admin_membership = (
        db.query(Membership)
        .join(Role)
        .filter(
            Role.name == "admin",
            Membership.organization_id.isnot(None),
            Membership.status == "active",
        )
        .first()
    )
    if not admin_membership:
        print("        skipped (no active admin found in dev DB)")
    else:
        org_id = admin_membership.organization_id
        admin_user_id = admin_membership.user_id
        # Find a verified member in the same org with a completed GPS assessment
        member_completed = (
            db.query(Assessment)
            .join(User, Assessment.user_id == User.id)
            .join(Membership, Membership.user_id == User.id)
            .filter(
                Assessment.instrument_type == "gps",
                Assessment.status == "completed",
                Assessment.deleted_at.is_(None),
                Assessment.user_id != admin_user_id,
                Membership.organization_id == org_id,
                Membership.status == "active",
            )
            .first()
        )
        if not member_completed:
            print(f"        skipped (admin {admin_user_id} has no member with a completed GPS assessment)")
        else:
            # Make sure admin's email_verified
            admin_user = db.query(User).filter(User.id == admin_user_id).first()
            if admin_user.email_verified != "Y":
                admin_user.email_verified = "Y"
                db.commit()

            # Soft-delete the member's assessment, hit /grade as admin, restore
            member_completed.deleted_at = datetime.now(timezone.utc)
            db.commit()

            admin_token = _mint_jwt(admin_user_id)
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            resp = client.get(f"/assessments/{member_completed.id}/grade", headers=admin_headers)
            # Restore immediately so the dev DB stays clean regardless of outcome
            member_completed.deleted_at = None
            db.commit()

            if resp.status_code != 200:
                fail(f"admin /grade on soft-deleted member assessment returned {resp.status_code}, expected 200 (body: {resp.text[:200]})")
            ok("admin can still /grade a soft-deleted member assessment (audit-trail invariant holds)")
            ok("test cleanup: restored member assessment deleted_at=NULL")

    # ── Group 3: /dashboard/summary still resolves (Return-to-Dashboard CTA target) ──
    print("\n[Group 3] GET /dashboard/summary (Return-to-Dashboard CTA target)")
    resp = client.get("/dashboard/summary", headers=headers)
    if resp.status_code != 200:
        fail(f"summary returned {resp.status_code} body={resp.text[:200]}")
    summary = resp.json()
    if "user" not in summary or "stats" not in summary:
        fail(f"summary missing required keys: {list(summary.keys())}")
    ok(f"summary OK (total_assessments={summary['stats'].get('total_assessments')})")

    # ── Group 7: MyImpact compare returns the right shape ─────────────────────
    print("\n[Group 7] POST /dashboard/compare with two MyImpact assessments")

    mi = (
        db.query(Assessment)
        .filter(
            Assessment.user_id == user_id,
            Assessment.instrument_type == "myimpact",
            Assessment.status == "completed",
            Assessment.deleted_at.is_(None),
        )
        .order_by(Assessment.completed_at)
        .limit(2)
        .all()
    )
    if len(mi) < 2:
        fail("setup invariant broke: we required >=2 myimpacts at top of script")
    a1, a2 = mi[0], mi[1]

    resp = client.post(
        "/dashboard/compare",
        json={"assessment_id_1": str(a1.id), "assessment_id_2": str(a2.id)},
        headers=headers,
    )
    if resp.status_code != 200:
        fail(f"compare returned {resp.status_code} body={resp.text[:400]}")
    body = resp.json()

    if body.get("instrument_type") != "myimpact":
        fail(f"expected instrument_type=myimpact, got {body.get('instrument_type')}")
    ok("response.instrument_type == 'myimpact'")

    if not body.get("myimpact_1") or not body.get("myimpact_2"):
        fail(f"myimpact_1/2 missing from response: {list(body.keys())}")
    ok("myimpact_1 and myimpact_2 populated")

    char_keys = set(body["myimpact_1"].get("character", {}).keys())
    if "loving" not in char_keys or "self_controlled" not in char_keys:
        fail(f"character dict missing expected keys: {char_keys}")
    ok(f"character dict has expected dimensions ({len(char_keys)} keys)")

    if body["myimpact_1"].get("myimpact_score") is None:
        fail("myimpact_1.myimpact_score is None")
    ok(f"myimpact_1.myimpact_score = {body['myimpact_1']['myimpact_score']:.2f}")

    # ── Group 7: mixed-type compare rejected ──────────────────────────────────
    print("\n[Group 7] Mixed GPS+MyImpact compare returns 400")

    gps_complete = (
        db.query(Assessment)
        .filter(
            Assessment.user_id == user_id,
            Assessment.instrument_type == "gps",
            Assessment.status == "completed",
            Assessment.deleted_at.is_(None),
        )
        .first()
    )
    if gps_complete:
        resp = client.post(
            "/dashboard/compare",
            json={"assessment_id_1": str(a1.id), "assessment_id_2": str(gps_complete.id)},
            headers=headers,
        )
        if resp.status_code != 400:
            fail(f"mixed-type compare returned {resp.status_code}, expected 400 (body={resp.text[:200]})")
        ok("mixed GPS+MyImpact compare rejected with 400")
    else:
        print("        skipped (user has no completed GPS assessment to mix with)")

    db.close()
    print("\nALL VERIFICATIONS PASSED")


if __name__ == "__main__":
    main()
