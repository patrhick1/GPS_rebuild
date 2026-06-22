"""Platform-wide outbound webhooks (Disciples Made's central Kit account).

Distinct from the per-organization webhook_service.py which handles
per-church Zapier configurations from Addendum §4. These four endpoints
fire to a single central destination owned by Disciples Made and let
their Kit/Zapier workflows tag/segment users across the platform.

URLs come from env vars (config.ZAPIER_*_URL). If a URL is unset
(dev/test), the corresponding trigger no-ops cleanly so local work
doesn't ping real Zapier endpoints.

Best-effort delivery: synchronous POST with a 10s timeout, no DB-backed
retry. Failures are logged but never block business logic. If we ever
see real missed-event reports from Jason, we'll add the same
retry/DLQ machinery that the per-org webhook_service uses; for the
v1 cut, Zapier Catch Hooks are reliable enough that the added
complexity isn't justified.

Idempotency for subscription events: gated on Subscription.zapier_*_at
columns set BEFORE the POST. The trade-off is explicit — we prefer
missing an event (which Jason can backfill from Stripe) over
double-firing into Kit and creating duplicate subscriber updates.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subscription import Subscription
from app.models.user import User
from app.services.webhook_service import TIMEOUT_SECONDS, assert_url_safe

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _post(url: str, payload: dict) -> None:
    """Best-effort POST. Logs on any failure; never raises."""
    try:
        assert_url_safe(url)
    except ValueError as exc:
        logger.warning("platform webhook URL rejected: %s (%s)", url, exc)
        return
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            resp = client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        if 200 <= resp.status_code < 300:
            logger.info(
                "platform webhook %s -> HTTP %s",
                payload.get("event"), resp.status_code,
            )
        else:
            logger.warning(
                "platform webhook %s -> HTTP %s: %s",
                payload.get("event"), resp.status_code, resp.text[:200],
            )
    except Exception as exc:  # pragma: no cover — defensive catchall
        logger.exception(
            "platform webhook %s POST raised: %s",
            payload.get("event"), exc,
        )


def is_toolkit_subscription(stripe_price_id: Optional[str]) -> bool:
    """True if the Stripe price_id matches a Toolkit plan (monthly or
    yearly). Today only Toolkit subscriptions exist, but the explicit
    check guards against future product additions accidentally firing
    the Kit webhooks. Empty-string config values are filtered out so
    a misconfigured env can't match an empty price_id."""
    if not stripe_price_id:
        return False
    known = {
        p for p in (settings.STRIPE_PRICE_MONTHLY, settings.STRIPE_PRICE_YEARLY) if p
    }
    return stripe_price_id in known


def _get_primary_admin(db: Session, organization_id) -> Optional[User]:
    """Return the active primary admin User for an organization, or None.

    Filters on User.status == 'active' so a (theoretically impossible)
    deleted-yet-still-primary admin can't leak `deleted_<id>@deleted.local`
    into the Zapier payload. delete_account currently blocks deletion of
    primary admins outright, but defense in depth is one filter clause.
    """
    from app.models.membership import Membership

    return (
        db.query(User)
        .join(Membership, Membership.user_id == User.id)
        .filter(
            Membership.organization_id == organization_id,
            Membership.is_primary_admin == True,  # noqa: E712 (SQLA filter)
            User.status == "active",
        )
        .first()
    )


# ─────────────────────────── Triggers ───────────────────────────


def fire_new_account(user: User, account_type: str) -> None:
    """Trigger 1: any user signs up (independent or church-attached).

    account_type is derived by the caller (auth_service) since the
    membership row may not exist yet at fire time. Values:
      - "independent"     — no org membership at registration
      - "church-attached" — joined a church via ?org= link OR created
                            a church via the church-register flow
    """
    url = settings.ZAPIER_NEW_ACCOUNT_URL
    if not url:
        return
    _post(url, {
        "event": "new_dashboard_account",
        "timestamp": _now_iso(),
        "user_id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "city": user.city,
        "state": user.state,
        "account_type": account_type,
    })


def fire_toolkit_activated(db: Session, subscription: Subscription) -> None:
    """Trigger 2: Toolkit subscription becomes active/trialing for the
    FIRST time per subscription.

    Caller (stripe_service.handle_subscription_updated) must have:
      - verified the price_id is a Toolkit price (via is_toolkit_subscription)
      - verified the status is active/trialing
      - COMMITTED any pending changes (we issue our own commit below
        and don't want to flush caller state by accident)

    Race protection: SELECT FOR UPDATE locks the row before the
    check-then-set so two concurrent Stripe webhook deliveries for
    the same subscription can't both pass the IS NULL check and
    double-fire. SQLAlchemy's identity map means the locked row IS
    `subscription` (same Python object), so we can keep using it
    after the lock — the lock just reflects fresh on-disk state.

    Sets zapier_activated_at = now() before POSTing so even a Zapier
    outage can't trigger a re-fire on the next webhook retry. We
    prefer occasional missed events (Jason can backfill from Stripe)
    over duplicate Kit subscriber updates.
    """
    db.execute(
        select(Subscription).where(Subscription.id == subscription.id).with_for_update()
    ).scalar_one()
    if subscription.zapier_activated_at is not None:
        db.commit()  # release the FOR UPDATE lock cleanly
        return
    subscription.zapier_activated_at = datetime.now(timezone.utc)
    db.commit()

    url = settings.ZAPIER_TOOLKIT_ACTIVATED_URL
    if not url:
        return

    from app.models.organization import Organization

    org = db.query(Organization).filter(
        Organization.id == subscription.organization_id,
    ).first()
    primary_user = _get_primary_admin(db, subscription.organization_id)

    _post(url, {
        "event": "toolkit_activated",
        "timestamp": _now_iso(),
        "user_id": str(primary_user.id) if primary_user else None,
        "church_id": str(subscription.organization_id),
        "email": primary_user.email if primary_user else None,
        "church_name": org.name if org else None,
        "church_city": org.city if org else None,
        "church_state": org.state if org else None,
        "subscription_status": subscription.status,
    })


def fire_toolkit_canceled(db: Session, subscription: Subscription) -> None:
    """Trigger 3: Toolkit subscription transitions to canceled / unpaid /
    incomplete_expired for the first time per subscription.

    Same caller preconditions and race-protection pattern as
    fire_toolkit_activated — see that docstring.
    """
    db.execute(
        select(Subscription).where(Subscription.id == subscription.id).with_for_update()
    ).scalar_one()
    if subscription.zapier_canceled_at is not None:
        db.commit()
        return
    subscription.zapier_canceled_at = datetime.now(timezone.utc)
    db.commit()

    url = settings.ZAPIER_TOOLKIT_CANCELED_URL
    if not url:
        return

    primary_user = _get_primary_admin(db, subscription.organization_id)

    _post(url, {
        "event": "toolkit_canceled",
        "timestamp": _now_iso(),
        "user_id": str(primary_user.id) if primary_user else None,
        "church_id": str(subscription.organization_id),
        "email": primary_user.email if primary_user else None,
        "subscription_status": subscription.status,
    })


def fire_user_deleted(user_id: UUID, email: str) -> None:
    """Trigger 4: self-service account deletion. Caller (auth_service.
    delete_account) MUST capture user_id and email before the
    anonymization block and pass them in — by the time the commit
    happens, user.email has been overwritten with `deleted_<id>@deleted.local`.
    """
    url = settings.ZAPIER_USER_DELETED_URL
    if not url:
        return
    _post(url, {
        "event": "user_deleted",
        "timestamp": _now_iso(),
        "user_id": str(user_id),
        "email": email,
    })
