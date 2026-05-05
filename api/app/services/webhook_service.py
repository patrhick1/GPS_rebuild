"""Webhook delivery service.

Builds, signs, sends, retries. Status lifecycle:
  pending -> success | failed -> success | failed -> ... -> dead

The retry runner picks up rows where status='failed' AND
next_retry_at <= now AND attempts < MAX_ATTEMPTS, with SELECT FOR UPDATE
SKIP LOCKED so multiple workers / cron firings can't double-deliver.

Why httpx instead of requests: already a transitive dep via FastAPI,
sync API matches the rest of the request handlers, supports HTTP/2 and
proper timeout semantics out of the box.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import socket
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery

logger = logging.getLogger(__name__)


MAX_ATTEMPTS = 4
TIMEOUT_SECONDS = 10.0
# Per PRD addendum §3.6: "Max 3 retry attempts. Backoff: 1 minute, 5 minutes,
# 30 minutes." That's three retries on top of the initial attempt — 4 attempts
# total. Index is the value of `attempts` AFTER the failure that just happened:
#   attempts=1 → +60s   (1st retry scheduled)
#   attempts=2 → +300s  (2nd retry scheduled)
#   attempts=3 → +1800s (3rd retry scheduled)
#   attempts=4 → dead   (no further retry)
BACKOFF_SECONDS = {1: 60, 2: 300, 3: 1800}


# -------------------- SSRF guard --------------------

def _is_blocked_host(host: str) -> bool:
    """Reject loopback, link-local, and private IP ranges. We resolve A records
    explicitly because trusting `host` text would let attackers stash an IP in
    a hostname and bypass us."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Unresolvable. Let the HTTP layer report the failure with a clear
        # error message rather than masking it as "blocked".
        return False

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast:
            return True
        # Reject the AWS / GCP metadata service explicitly. is_link_local
        # already covers 169.254.0.0/16 but be explicit for the common case.
        if str(ip) == "169.254.169.254":
            return True
    return False


def assert_url_safe(url: str) -> None:
    """Raise ValueError if URL points at internal infra. Called at config save
    AND at delivery time (DNS may have changed since the URL was saved)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Webhook URL scheme must be http or https, got {parsed.scheme!r}")
    if not parsed.hostname:
        raise ValueError("Webhook URL missing hostname")
    if _is_blocked_host(parsed.hostname):
        raise ValueError(
            "Webhook URL resolves to a private / loopback / link-local IP, which is not allowed"
        )


# -------------------- Service --------------------

class WebhookService:
    def __init__(self, db: Session):
        self.db = db

    # ---- Config CRUD ----

    def list_configs_for_org(self, organization_id: UUID) -> list[WebhookConfig]:
        return (
            self.db.query(WebhookConfig)
            .filter(WebhookConfig.organization_id == organization_id)
            .order_by(WebhookConfig.event_type)
            .all()
        )

    def get_config(self, config_id: UUID) -> Optional[WebhookConfig]:
        return self.db.query(WebhookConfig).filter(WebhookConfig.id == config_id).first()

    def create_config(
        self,
        *,
        organization_id: UUID,
        event_type: str,
        webhook_url: str,
        is_active: bool = True,
        generate_secret: bool = False,
    ) -> Tuple[WebhookConfig, Optional[str]]:
        """Create a new webhook config. Returns (config, plaintext_secret_or_None).
        Plaintext secret is shown once and never again."""
        assert_url_safe(webhook_url)
        plaintext = None
        if generate_secret:
            plaintext = secrets.token_urlsafe(32)

        config = WebhookConfig(
            organization_id=organization_id,
            event_type=event_type,
            webhook_url=webhook_url,
            is_active=is_active,
            secret=plaintext,
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config, plaintext

    def update_config(
        self,
        config: WebhookConfig,
        *,
        webhook_url: Optional[str] = None,
        is_active: Optional[bool] = None,
        generate_secret: Optional[bool] = None,
    ) -> Tuple[WebhookConfig, Optional[str]]:
        plaintext = None
        if webhook_url is not None:
            assert_url_safe(webhook_url)
            config.webhook_url = webhook_url
        if is_active is not None:
            config.is_active = is_active
        if generate_secret:
            plaintext = secrets.token_urlsafe(32)
            config.secret = plaintext
        self.db.commit()
        self.db.refresh(config)
        return config, plaintext

    def delete_config(self, config: WebhookConfig) -> None:
        self.db.delete(config)
        self.db.commit()

    # ---- Dispatch ----

    def fire(
        self, organization_id: UUID, event_type: str, payload: dict
    ) -> Optional[WebhookDelivery]:
        """Look up the active config for (org, event_type). If none, no-op.
        Otherwise create a delivery row and attempt synchronous delivery.
        Always commits so the log row exists even on failure."""
        config = (
            self.db.query(WebhookConfig)
            .filter(
                WebhookConfig.organization_id == organization_id,
                WebhookConfig.event_type == event_type,
                WebhookConfig.is_active.is_(True),
            )
            .first()
        )
        if not config:
            return None

        delivery = WebhookDelivery(
            webhook_config_id=config.id,
            event_type=event_type,
            payload=payload,
            status="pending",
            attempts=0,
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)

        self._deliver(delivery, config)
        return delivery

    def _deliver(
        self,
        delivery: WebhookDelivery,
        config: WebhookConfig,
        *,
        commit: bool = True,
    ) -> None:
        """Attempt one delivery and update the row's status fields.

        ``commit=True`` is correct for the synchronous fire() path, where
        each delivery is its own short transaction. The retry runner sets
        ``commit=False`` so the outer SELECT FOR UPDATE lock isn't released
        between rows in the batch — that release would let a concurrent
        cron pick up the same rows and double-deliver them.
        """
        body_bytes = json.dumps(delivery.payload, default=str).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-GPS-Event": delivery.event_type,
            "X-GPS-Delivery-Id": str(delivery.id),
        }
        if config.secret:
            sig = hmac.new(
                config.secret.encode("utf-8"), body_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-GPS-Signature"] = f"sha256={sig}"

        delivery.attempts = (delivery.attempts or 0) + 1
        try:
            assert_url_safe(config.webhook_url)
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                resp = client.post(config.webhook_url, content=body_bytes, headers=headers)
            delivery.http_status_code = resp.status_code
            if 200 <= resp.status_code < 300:
                delivery.status = "success"
                delivery.error_message = None
                delivery.next_retry_at = None
            else:
                self._mark_failed(
                    delivery,
                    error=f"HTTP {resp.status_code}: {resp.text[:500]}",
                )
        except (httpx.RequestError, ValueError) as exc:
            self._mark_failed(delivery, error=f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # pragma: no cover — defensive catchall
            self._mark_failed(delivery, error=f"{type(exc).__name__}: {exc}")
            logger.exception("Unexpected webhook delivery error")
        finally:
            if commit:
                self.db.commit()

    def _mark_failed(self, delivery: WebhookDelivery, *, error: str) -> None:
        delivery.error_message = error
        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = "dead"
            delivery.next_retry_at = None
        else:
            delivery.status = "failed"
            delivery.next_retry_at = datetime.utcnow() + timedelta(
                seconds=BACKOFF_SECONDS.get(delivery.attempts, 0)
            )

    # ---- Retry runner ----

    def process_pending_retries(self, batch_size: int = 50) -> int:
        """Called by the internal cron endpoint. Returns count processed.

        Uses SELECT FOR UPDATE SKIP LOCKED to claim a batch of rows. The
        locks are held for the duration of the batch — we deliberately do
        NOT commit between rows so a concurrent cron firing can't release
        them mid-flight and double-deliver the rest. With max_attempts=4
        and batch_size=50 the worst-case lock duration is bounded by
        50 × TIMEOUT_SECONDS (≈8 min for a fully-failing batch); the next
        cron simply skips the locked rows and picks up other work.

        Postgres-only; SQLite (dev) doesn't support SKIP LOCKED but cron
        is never wired up in dev.
        """
        rows = self.db.execute(
            text(
                """
                SELECT id FROM webhook_deliveries
                 WHERE status = 'failed'
                   AND next_retry_at <= NOW()
                   AND attempts < :max_attempts
                 ORDER BY next_retry_at ASC
                 LIMIT :batch_size
                 FOR UPDATE SKIP LOCKED
                """
            ),
            {"max_attempts": MAX_ATTEMPTS, "batch_size": batch_size},
        ).fetchall()

        ids = [r[0] for r in rows]
        if not ids:
            return 0

        try:
            deliveries = (
                self.db.query(WebhookDelivery)
                .filter(WebhookDelivery.id.in_(ids))
                .all()
            )
            # Fetch all configs in one round-trip.
            config_ids = {d.webhook_config_id for d in deliveries}
            configs_by_id = {
                c.id: c
                for c in self.db.query(WebhookConfig)
                .filter(WebhookConfig.id.in_(config_ids))
                .all()
            }

            for delivery in deliveries:
                config = configs_by_id.get(delivery.webhook_config_id)
                if not config:
                    # Config was deleted out from under us. Mark dead so we
                    # stop retrying — there's nothing to deliver to.
                    delivery.status = "dead"
                    delivery.next_retry_at = None
                    delivery.error_message = "Webhook config was deleted"
                    continue
                # Critical: commit=False keeps the SELECT FOR UPDATE locks
                # held until the loop ends. See docstring above.
                self._deliver(delivery, config, commit=False)

            self.db.commit()
            return len(deliveries)
        except Exception:
            # On unexpected error, roll back so the batch reverts to its
            # pre-claim state. SKIP LOCKED + status='failed' filter will
            # pick the rows up again on the next cron tick.
            self.db.rollback()
            logger.exception("process_pending_retries batch failed; rolled back")
            raise

    # ---- Test connection ----

    def test_delivery(self, config: WebhookConfig, payload: dict) -> dict:
        """Synchronously POST a test payload. Does NOT write to webhook_deliveries
        — test pings shouldn't pollute the production delivery log."""
        body_bytes = json.dumps(payload, default=str).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-GPS-Event": config.event_type,
            "X-GPS-Test": "true",
        }
        if config.secret:
            sig = hmac.new(
                config.secret.encode("utf-8"), body_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-GPS-Signature"] = f"sha256={sig}"

        try:
            assert_url_safe(config.webhook_url)
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                resp = client.post(config.webhook_url, content=body_bytes, headers=headers)
            ok = 200 <= resp.status_code < 300
            return {
                "ok": ok,
                "status_code": resp.status_code,
                "error": None if ok else f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
        except (httpx.RequestError, ValueError) as exc:
            return {"ok": False, "status_code": None, "error": f"{type(exc).__name__}: {exc}"}
