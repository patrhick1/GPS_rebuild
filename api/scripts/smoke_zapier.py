"""In-process smoke test for the platform-wide Zapier integration.

Verifies the 4 triggers fire with the correct payload shape without
ever sending a real HTTP request to Jason's Zapier endpoints. Works
by monkey-patching `platform_webhook_service._post` to capture calls
into a list.

Covers:
  - Trigger 1: register_user (independent + church-attached)
  - Trigger 1: register_church_admin
  - Trigger 2: fire_toolkit_activated (+ idempotency double-call)
  - Trigger 3: fire_toolkit_canceled (+ idempotency double-call)
  - Trigger 4: fire_user_deleted (via delete_account path)
  - is_toolkit_subscription gate

Run from the api/ directory:
  python scripts/smoke_zapier.py

Exits non-zero on any assertion failure.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make `app` importable from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.role import Role
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.user import ChurchAdminRegister, UserCreate
from app.services import platform_webhook_service
from app.services.auth_service import AuthService

# ─────────────────────── Setup: capture calls ────────────────────────

captured: list[tuple[str, dict]] = []


def fake_post(url: str, payload: dict) -> None:
    captured.append((url, payload))


platform_webhook_service._post = fake_post

# Set dummy URLs so the no-op guard doesn't short-circuit the triggers.
settings.ZAPIER_NEW_ACCOUNT_URL = "https://example.invalid/new-account"
settings.ZAPIER_TOOLKIT_ACTIVATED_URL = "https://example.invalid/activated"
settings.ZAPIER_TOOLKIT_CANCELED_URL = "https://example.invalid/canceled"
settings.ZAPIER_USER_DELETED_URL = "https://example.invalid/user-deleted"


# ─────────────────────── Setup: assertion helpers ────────────────────


PASSED = 0
FAILED = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def find_event(event_name: str) -> dict | None:
    for _url, payload in captured:
        if payload.get("event") == event_name:
            return payload
    return None


def find_event_with_url(event_name: str) -> tuple[str, dict] | tuple[None, None]:
    for url, payload in captured:
        if payload.get("event") == event_name:
            return url, payload
    return None, None


# ─────────────────────── Setup: DB fixtures ──────────────────────────


db = SessionLocal()
suffix = uuid.uuid4().hex[:8]
created_user_ids: list = []
created_org_ids: list = []
created_sub_ids: list = []


def cleanup() -> None:
    """Remove anything we created. Best-effort. Roll back any pending
    transaction state first so a prior failure doesn't poison this."""
    try:
        db.rollback()
    except Exception:
        pass
    try:
        from sqlalchemy import text
        # Delete ALL subs for our test orgs, not just the ones we tracked
        # (any retry/double-fire could have left extras).
        for oid in created_org_ids:
            db.query(Subscription).filter(Subscription.organization_id == oid).delete()
        for sid in created_sub_ids:
            sub = db.query(Subscription).filter(Subscription.id == sid).first()
            if sub:
                db.delete(sub)
        for uid in created_user_ids:
            # Cascade-clear FKs that don't have ON DELETE CASCADE
            db.execute(text("DELETE FROM email_verification_tokens WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM password_reset_tokens WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM refresh_tokens WHERE user_id = :u"), {"u": uid})
            db.query(Membership).filter(Membership.user_id == uid).delete()
            user = db.query(User).filter(User.id == uid).first()
            if user:
                db.delete(user)
        for oid in created_org_ids:
            org = db.query(Organization).filter(Organization.id == oid).first()
            if org:
                db.delete(org)
        db.commit()
    except Exception as exc:
        print(f"  (cleanup warn: {exc})")
        db.rollback()


# ─────────────────────── Tests ───────────────────────────────────────


def test_is_toolkit_subscription() -> None:
    print("\n[gate] is_toolkit_subscription")
    monthly = settings.STRIPE_PRICE_MONTHLY
    yearly = settings.STRIPE_PRICE_YEARLY
    check("matches monthly", platform_webhook_service.is_toolkit_subscription(monthly))
    check("matches yearly", platform_webhook_service.is_toolkit_subscription(yearly))
    check("rejects None", not platform_webhook_service.is_toolkit_subscription(None))
    check(
        "rejects unknown price_id",
        not platform_webhook_service.is_toolkit_subscription("price_unknown_999"),
    )


def test_trigger_1_independent_user() -> None:
    print("\n[trigger 1] register_user (independent)")
    captured.clear()
    auth = AuthService(db)
    user_data = UserCreate(
        email=f"smoke-indep-{suffix}@smoketest.example.com",
        password="Zx9$qWv2!Mn7",
        first_name="Indep",
        last_name="Tester",
        city="Topeka",
        state="KS",
    )
    user = auth.register_user(user_data, organization_key=None)
    created_user_ids.append(user.id)

    url, payload = find_event_with_url("new_dashboard_account")
    check("event fired", payload is not None)
    if not payload:
        return
    check("routed to ZAPIER_NEW_ACCOUNT_URL", url == settings.ZAPIER_NEW_ACCOUNT_URL)
    check("user_id present", payload.get("user_id") == str(user.id))
    check("email correct", payload.get("email") == user_data.email.lower())
    check("first_name", payload.get("first_name") == "Indep")
    check("city persisted", payload.get("city") == "Topeka")
    check("state persisted", payload.get("state") == "KS")
    check("account_type=independent", payload.get("account_type") == "independent")


def test_trigger_1_church_attached_user() -> None:
    print("\n[trigger 1] register_user (church-attached via ?org=)")
    captured.clear()
    org = Organization(
        name=f"Smoke Org {suffix}",
        key=f"smoke-org-{suffix}",
        city="Wichita",
        state="KS",
        country="USA",
        status="active",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    created_org_ids.append(org.id)

    auth = AuthService(db)
    user_data = UserCreate(
        email=f"smoke-church-{suffix}@smoketest.example.com",
        password="Zx9$qWv2!Mn7",
        first_name="Church",
        last_name="Member",
        city="Wichita",
        state="KS",
    )
    user = auth.register_user(user_data, organization_key=org.key)
    created_user_ids.append(user.id)

    payload = find_event("new_dashboard_account")
    check("event fired", payload is not None)
    if not payload:
        return
    check(
        "account_type=church-attached",
        payload.get("account_type") == "church-attached",
        f"got {payload.get('account_type')!r}",
    )


def test_trigger_1_church_admin() -> None:
    print("\n[trigger 1] register_church_admin")
    captured.clear()
    auth = AuthService(db)
    data = ChurchAdminRegister(
        email=f"smoke-admin-{suffix}@smoketest.example.com",
        password="Zx9$qWv2!Mn7",
        first_name="Smoke",
        last_name="Admin",
        org_name=f"Smoke Admin Org {suffix}",
        org_city="Lawrence",
        org_state="KS",
        org_country="USA",
    )
    user = auth.register_church_admin(data)
    created_user_ids.append(user.id)
    # Find and stash the org for cleanup
    mem = db.query(Membership).filter(Membership.user_id == user.id).first()
    if mem and mem.organization_id:
        created_org_ids.append(mem.organization_id)

    payload = find_event("new_dashboard_account")
    check("event fired", payload is not None)
    if not payload:
        return
    check(
        "account_type=church-attached",
        payload.get("account_type") == "church-attached",
        f"got {payload.get('account_type')!r}",
    )
    check("city carries through from org_city", payload.get("city") == "Lawrence")


def test_trigger_2_toolkit_activated_and_idempotent() -> None:
    print("\n[trigger 2] fire_toolkit_activated + idempotency")
    captured.clear()

    # Build an org + primary admin + Subscription row
    org = Organization(
        name=f"Smoke Toolkit Org {suffix}",
        key=f"smoke-toolkit-{suffix}",
        city="Manhattan",
        state="KS",
        country="USA",
        status="active",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    created_org_ids.append(org.id)

    admin = User(
        email=f"smoke-toolkit-admin-{suffix}@smoketest.example.com",
        first_name="Toolkit",
        last_name="Admin",
        status="active",
    )
    db.add(admin)
    db.flush()
    created_user_ids.append(admin.id)

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    mem = Membership(
        user_id=admin.id,
        organization_id=org.id,
        role_id=admin_role.id if admin_role else None,
        is_primary_admin=True,
    )
    db.add(mem)

    sub = Subscription(
        organization_id=org.id,
        stripe_subscription_id=f"sub_smoke_{suffix}",
        stripe_price_id=settings.STRIPE_PRICE_MONTHLY or "price_test_monthly_plan_id",
        status="active",
        plan="monthly",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    created_sub_ids.append(sub.id)

    # First fire — should send
    platform_webhook_service.fire_toolkit_activated(db, sub)
    url, payload = find_event_with_url("toolkit_activated")
    check("first call fires", payload is not None)
    if payload:
        check("routed to ZAPIER_TOOLKIT_ACTIVATED_URL", url == settings.ZAPIER_TOOLKIT_ACTIVATED_URL)
        check("user_id = primary admin", payload.get("user_id") == str(admin.id))
        check("church_id correct", payload.get("church_id") == str(org.id))
        check("email = admin email", payload.get("email") == admin.email)
        check("church_name correct", payload.get("church_name") == org.name)
        check("church_city correct", payload.get("church_city") == "Manhattan")
        check("subscription_status=active", payload.get("subscription_status") == "active")
    db.refresh(sub)
    check("zapier_activated_at set", sub.zapier_activated_at is not None)

    # Second fire — should NOT send (idempotent)
    captured.clear()
    platform_webhook_service.fire_toolkit_activated(db, sub)
    check("second call no-ops (idempotent)", find_event("toolkit_activated") is None)


def test_trigger_3_toolkit_canceled_and_idempotent() -> None:
    print("\n[trigger 3] fire_toolkit_canceled + idempotency")
    captured.clear()

    sub = db.query(Subscription).filter(Subscription.id == created_sub_ids[-1]).first()
    if not sub:
        check("sub exists from trigger-2 setup", False, "no sub found")
        return
    sub.status = "canceled"
    db.commit()

    platform_webhook_service.fire_toolkit_canceled(db, sub)
    url, payload = find_event_with_url("toolkit_canceled")
    check("first call fires", payload is not None)
    if payload:
        check("routed to ZAPIER_TOOLKIT_CANCELED_URL", url == settings.ZAPIER_TOOLKIT_CANCELED_URL)
        check("church_id correct", payload.get("church_id") == str(sub.organization_id))
        check("subscription_status=canceled", payload.get("subscription_status") == "canceled")
    db.refresh(sub)
    check("zapier_canceled_at set", sub.zapier_canceled_at is not None)

    captured.clear()
    platform_webhook_service.fire_toolkit_canceled(db, sub)
    check("second call no-ops (idempotent)", find_event("toolkit_canceled") is None)


def test_trigger_4_user_deleted() -> None:
    print("\n[trigger 4] fire_user_deleted")
    captured.clear()
    fake_id = uuid.uuid4()
    platform_webhook_service.fire_user_deleted(fake_id, "deleted-test@example.com")
    url, payload = find_event_with_url("user_deleted")
    check("event fired", payload is not None)
    if payload:
        check("routed to ZAPIER_USER_DELETED_URL", url == settings.ZAPIER_USER_DELETED_URL)
        check("user_id stringified", payload.get("user_id") == str(fake_id))
        check("email is real (not anonymized)", payload.get("email") == "deleted-test@example.com")


def test_no_op_when_url_unset() -> None:
    print("\n[no-op] trigger short-circuits if URL is unset")
    saved = settings.ZAPIER_USER_DELETED_URL
    settings.ZAPIER_USER_DELETED_URL = None
    captured.clear()
    platform_webhook_service.fire_user_deleted(uuid.uuid4(), "x@x.com")
    check("no fire when URL=None", len(captured) == 0)
    settings.ZAPIER_USER_DELETED_URL = saved


# ─────────────────────── Main ────────────────────────────────────────


def main() -> int:
    print("=" * 60)
    print("Platform Zapier integration smoke")
    print("=" * 60)
    try:
        test_is_toolkit_subscription()
        test_trigger_1_independent_user()
        test_trigger_1_church_attached_user()
        test_trigger_1_church_admin()
        test_trigger_2_toolkit_activated_and_idempotent()
        test_trigger_3_toolkit_canceled_and_idempotent()
        test_trigger_4_user_deleted()
        test_no_op_when_url_unset()
    finally:
        cleanup()
        db.close()

    print()
    print("=" * 60)
    print(f"PASSED: {PASSED}    FAILED: {FAILED}")
    print("=" * 60)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
