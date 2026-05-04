"""End-to-end smoke tests against the live Render DB.

Creates real (test-scoped) rows, exercises the service layer the way Phase
C wires it, then cleans up. Use a randomly-generated test org so we don't
pollute real data.
"""
print("[start]", flush=True)
import os
import sys
import uuid
import traceback
from datetime import datetime, timezone

sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery
from app.services import notification_service
from app.services.webhook_service import WebhookService
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


# -------- fixtures
print("[setup]", flush=True)


def _fixtures(db: Session):
    """Create a transient org + admin + member for testing.
    Returns (org, admin_user, member_user, role_admin, role_member)."""
    role_admin = db.query(Role).filter(Role.name == "admin").first()
    role_member = db.query(Role).filter(Role.name == "member").first()
    assert role_admin is not None, "admin role missing — db_seed not run?"
    assert role_member is not None, "member role missing"

    suffix = uuid.uuid4().hex[:8]
    org = Organization(
        name=f"SmokeTest Church {suffix}",
        key=f"smoke-test-{suffix}",
        status="active",
        is_comped=True,  # bypass subscription gate
    )
    db.add(org); db.flush()

    admin = User(
        email=f"smoke-admin-{suffix}@example.com",
        password_hash="x" * 60,
        first_name="Smoke", last_name="Admin",
        status="active", email_verified="Y",
    )
    member = User(
        email=f"smoke-member-{suffix}@example.com",
        password_hash="x" * 60,
        first_name="Smoke", last_name="Member",
        status="active", email_verified="Y",
    )
    db.add(admin); db.add(member); db.flush()

    db.add(Membership(user_id=admin.id, organization_id=org.id, role_id=role_admin.id, is_primary_admin=True, status="active"))
    db.add(Membership(user_id=member.id, organization_id=org.id, role_id=role_member.id, status="active"))
    db.commit()
    return org, admin, member


def _cleanup(db: Session, org_id, user_ids):
    """Best-effort cleanup."""
    db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_config_id.in_(
            db.query(WebhookConfig.id).filter(WebhookConfig.organization_id == org_id)
        )
    ).delete(synchronize_session=False)
    db.query(WebhookConfig).filter(WebhookConfig.organization_id == org_id).delete()
    db.query(Notification).filter(Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(Membership).filter(Membership.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.query(Organization).filter(Organization.id == org_id).delete()
    db.commit()


# -------- Run tests
db = SessionLocal()
org, admin, member = _fixtures(db)
print(f"  [fixture] org={org.id} admin={admin.id} member={member.id}", flush=True)

try:
    # ---- Notifications round-trip
    print("[notifications]", flush=True)

    def t_create_then_read():
        n = notification_service.create_notification(
            db, user_id=admin.id, type="assessment_completed",
            title="Test note", message="Smoke test message",
            link="/admin", reference_type="assessment", reference_id=uuid.uuid4(),
        )
        assert n.id is not None
        assert n.is_read is False
        # Read it back
        out = notification_service.get_notifications(db, admin.id, limit=10)
        assert out["unread_count"] >= 1
        assert any(x.id == n.id for x in out["notifications"])

    run("create_notification + get_notifications round-trip", t_create_then_read)

    def t_mark_read():
        n = notification_service.create_notification(
            db, user_id=admin.id, type="member_joined",
            title="X joined", message="welcome",
        )
        ok = notification_service.mark_read(db, n.id, admin.id)
        assert ok is True
        db.refresh(n)
        assert n.is_read is True

    run("mark_read flips is_read to True", t_mark_read)

    def t_mark_all_read():
        for i in range(3):
            notification_service.create_notification(
                db, user_id=admin.id, type="member_requested",
                title=f"req {i}", message="...")
        before = notification_service.get_unread_count(db, admin.id)
        assert before >= 3
        notification_service.mark_all_read(db, admin.id)
        after = notification_service.get_unread_count(db, admin.id)
        assert after == 0, f"after mark_all_read: {after}"

    run("mark_all_read clears unread count", t_mark_all_read)

    # ---- Webhook config CRUD
    print("[webhook-configs]", flush=True)
    svc = WebhookService(db)

    def t_create_config_with_secret():
        config, plaintext = svc.create_config(
            organization_id=org.id,
            event_type="assessment_completed",
            webhook_url="https://httpbin.org/post",
            generate_secret=True,
        )
        assert config.id is not None
        assert plaintext is not None and len(plaintext) > 20, f"secret length: {plaintext}"
        assert config.secret == plaintext, "DB-stored secret should equal plaintext (returned once)"

    run("create_config returns plaintext secret + persists", t_create_config_with_secret)

    def t_unique_constraint():
        try:
            svc.create_config(
                organization_id=org.id,
                event_type="assessment_completed",  # same as above
                webhook_url="https://example.com/x",
            )
            raise AssertionError("Expected unique-constraint failure")
        except Exception as e:
            db.rollback()
            assert "unique" in str(e).lower() or "duplicate" in str(e).lower() or "uq_webhook_configs_org_event" in str(e), str(e)

    run("UNIQUE (org_id, event_type) prevents duplicate config", t_unique_constraint)

    def t_ssrf_at_save_time():
        try:
            svc.create_config(
                organization_id=org.id,
                event_type="user_registered",  # different event so no UNIQUE conflict
                webhook_url="http://10.0.0.1/x",
            )
            raise AssertionError("Expected ValueError from SSRF guard")
        except ValueError as e:
            assert "private" in str(e).lower(), str(e)

    run("create_config rejects private-IP URL via SSRF guard", t_ssrf_at_save_time)

    # ---- Webhook fire end-to-end
    print("[webhook-fire]", flush=True)

    def t_fire_creates_delivery_row_success():
        before = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_config_id.in_(
                db.query(WebhookConfig.id).filter(WebhookConfig.organization_id == org.id)
            )
        ).count()
        payload = build_test_assessment_payload(event_type="assessment_completed")
        delivery = svc.fire(org.id, "assessment_completed", payload)
        assert delivery is not None, "fire returned None — config not found?"
        db.refresh(delivery)
        assert delivery.status == "success", f"status={delivery.status} error={delivery.error_message}"
        assert delivery.http_status_code == 200, f"http={delivery.http_status_code}"
        assert delivery.attempts == 1
        assert delivery.next_retry_at is None
        after = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_config_id.in_(
                db.query(WebhookConfig.id).filter(WebhookConfig.organization_id == org.id)
            )
        ).count()
        assert after == before + 1

    run("fire() against httpbin -> status=success, attempts=1, log row written", t_fire_creates_delivery_row_success)

    def t_fire_unconfigured_event_no_op():
        # No config exists for user_registered (the SSRF attempt didn't persist).
        result = svc.fire(org.id, "user_registered", {"event": "user_registered", "test": True})
        assert result is None, "fire should be a no-op when no config exists"

    run("fire() with no matching config returns None (no-op)", t_fire_unconfigured_event_no_op)

    def t_fire_failure_schedules_retry():
        # Create a config pointing at an httpbin endpoint that returns 500.
        bad_config, _ = svc.create_config(
            organization_id=org.id,
            event_type="user_registered",
            webhook_url="https://httpbin.org/status/500",
        )
        delivery = svc.fire(org.id, "user_registered", {"event": "user_registered", "test": True})
        assert delivery is not None
        db.refresh(delivery)
        assert delivery.status == "failed", f"status={delivery.status}"
        assert delivery.attempts == 1
        assert delivery.next_retry_at is not None
        # Backoff is 60s for first failure.
        assert (delivery.next_retry_at - datetime.utcnow()).total_seconds() > 30, "should be ~60s in future"

    run("fire() against 500 -> status=failed, attempts=1, next_retry_at scheduled", t_fire_failure_schedules_retry)

    def t_test_delivery_no_log_row():
        # test_delivery() should NOT pollute webhook_deliveries.
        config = db.query(WebhookConfig).filter(
            WebhookConfig.organization_id == org.id,
            WebhookConfig.event_type == "assessment_completed",
        ).first()
        before = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_config_id == config.id
        ).count()
        result = svc.test_delivery(config, build_test_assessment_payload(event_type="assessment_completed"))
        after = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_config_id == config.id
        ).count()
        assert after == before, f"test_delivery created {after - before} rows; expected 0"
        assert result["ok"] is True, f"result: {result}"

    run("test_delivery() does NOT write to webhook_deliveries", t_test_delivery_no_log_row)

finally:
    print("[cleanup]", flush=True)
    _cleanup(db, org.id, [admin.id, member.id])
    db.close()


print(f"\n[summary] PASS={PASS} FAIL={FAIL}", flush=True)
sys.exit(0 if FAIL == 0 else 1)
