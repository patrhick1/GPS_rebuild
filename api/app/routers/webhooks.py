"""Webhook configuration + delivery API.

Admin: full CRUD on their org's webhooks, plus test + delivery log views.
Master: read-only view of any org's webhooks.
Internal: cron-driven retry processor (shared-secret auth).
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limits import limiter, ADMIN_RATE
from app.dependencies.auth import require_admin, require_master
from app.models.user import User
from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery
from app.routers.admin import get_admin_organization
from app.schemas.webhook import (
    CronProcessRetriesResponse,
    MasterWebhookConfigResponse,
    MasterWebhookListResponse,
    WebhookConfigCreate,
    WebhookConfigCreatedResponse,
    WebhookConfigListResponse,
    WebhookConfigResponse,
    WebhookConfigUpdate,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookTestResponse,
)
from app.services.webhook_payloads import build_test_assessment_payload
from app.services.webhook_service import WebhookService


router = APIRouter(prefix="/admin/webhooks", tags=["Webhooks"])
master_router = APIRouter(prefix="/master/organizations", tags=["Webhooks (Master)"])
internal_router = APIRouter(prefix="/internal/webhooks", tags=["Webhooks (Internal)"])


# ---------- helpers ----------

def _mask_secret(secret: Optional[str]) -> Optional[str]:
    if not secret:
        return None
    if len(secret) <= 4:
        return "•" * len(secret)
    return f"••••{secret[-4:]}"


def _mask_url(url: str) -> str:
    """https://hooks.zapier.com/hooks/catch/abcd1234/ -> https://hooks.zapier.com/hooks/catch/••••1234/"""
    if not url:
        return ""
    if len(url) <= 12:
        return "•" * len(url)
    return f"{url[:30]}…{url[-6:]}" if len(url) > 36 else url


def _to_response(config: WebhookConfig) -> WebhookConfigResponse:
    return WebhookConfigResponse(
        id=config.id,
        organization_id=config.organization_id,
        event_type=config.event_type,
        webhook_url=config.webhook_url,
        is_active=config.is_active,
        has_secret=bool(config.secret),
        secret_masked=_mask_secret(config.secret),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def _ensure_admin_owns(config: WebhookConfig, current_user: User, db: Session) -> None:
    org = get_admin_organization(db, current_user)
    if config.organization_id != org.id:
        # Don't leak existence: respond as if it didn't exist.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


# ---------- Admin endpoints ----------

@router.get("", response_model=WebhookConfigListResponse)
@limiter.limit(ADMIN_RATE)
async def list_webhooks(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    org = get_admin_organization(db, current_user)
    configs = WebhookService(db).list_configs_for_org(org.id)
    return WebhookConfigListResponse(webhooks=[_to_response(c) for c in configs])


@router.post("", response_model=WebhookConfigCreatedResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(ADMIN_RATE)
async def create_webhook(
    request: Request,
    body: WebhookConfigCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    org = get_admin_organization(db, current_user)

    # Pre-check uniqueness so we return a clean 409 instead of an integrity error.
    existing = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.organization_id == org.id,
            WebhookConfig.event_type == body.event_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A webhook for event_type '{body.event_type}' already exists for this church",
        )

    try:
        config, plaintext = WebhookService(db).create_config(
            organization_id=org.id,
            event_type=body.event_type,
            webhook_url=str(body.webhook_url),
            is_active=body.is_active,
            generate_secret=body.generate_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    base = _to_response(config)
    return WebhookConfigCreatedResponse(
        **base.model_dump(),
        secret_plaintext=plaintext,
    )


@router.get("/{webhook_id}", response_model=WebhookConfigResponse)
@limiter.limit(ADMIN_RATE)
async def get_webhook(
    request: Request,
    webhook_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    config = WebhookService(db).get_config(webhook_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    _ensure_admin_owns(config, current_user, db)
    return _to_response(config)


@router.put("/{webhook_id}", response_model=WebhookConfigCreatedResponse)
@limiter.limit(ADMIN_RATE)
async def update_webhook(
    request: Request,
    webhook_id: UUID,
    body: WebhookConfigUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = WebhookService(db)
    config = service.get_config(webhook_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    _ensure_admin_owns(config, current_user, db)

    try:
        config, plaintext = service.update_config(
            config,
            webhook_url=str(body.webhook_url) if body.webhook_url else None,
            is_active=body.is_active,
            generate_secret=body.generate_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    base = _to_response(config)
    return WebhookConfigCreatedResponse(
        **base.model_dump(),
        secret_plaintext=plaintext,
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(ADMIN_RATE)
async def delete_webhook(
    request: Request,
    webhook_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = WebhookService(db)
    config = service.get_config(webhook_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    _ensure_admin_owns(config, current_user, db)
    service.delete_config(config)
    return None


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
@limiter.limit(ADMIN_RATE)
async def test_webhook(
    request: Request,
    webhook_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Synchronously fire a test payload. Does not write to delivery log."""
    service = WebhookService(db)
    config = service.get_config(webhook_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    _ensure_admin_owns(config, current_user, db)

    payload = build_test_assessment_payload(event_type=config.event_type)
    result = service.test_delivery(config, payload)
    return WebhookTestResponse(**result)


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
@limiter.limit(ADMIN_RATE)
async def list_deliveries(
    request: Request,
    webhook_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = WebhookService(db)
    config = service.get_config(webhook_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    _ensure_admin_owns(config, current_user, db)

    cutoff = datetime.utcnow() - timedelta(days=30)
    query = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_config_id == config.id,
        WebhookDelivery.created_at >= cutoff,
    )
    if status_filter:
        query = query.filter(WebhookDelivery.status == status_filter)

    total = query.count()
    rows = (
        query.order_by(WebhookDelivery.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return WebhookDeliveryListResponse(
        deliveries=[WebhookDeliveryResponse.model_validate(r) for r in rows],
        total_count=total,
    )


# ---------- Master endpoint ----------

@master_router.get("/{organization_id}/webhooks", response_model=MasterWebhookListResponse)
@limiter.limit(ADMIN_RATE)
async def master_list_webhooks(
    request: Request,
    organization_id: UUID,
    current_user: User = Depends(require_master),
    db: Session = Depends(get_db),
):
    """Read-only master view of any org's webhooks. URLs masked, secrets never exposed."""
    configs = WebhookService(db).list_configs_for_org(organization_id)

    out: list[MasterWebhookConfigResponse] = []
    for c in configs:
        last = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.webhook_config_id == c.id)
            .order_by(WebhookDelivery.created_at.desc())
            .first()
        )
        out.append(
            MasterWebhookConfigResponse(
                id=c.id,
                organization_id=c.organization_id,
                event_type=c.event_type,
                webhook_url_masked=_mask_url(c.webhook_url),
                is_active=c.is_active,
                has_secret=bool(c.secret),
                last_delivery_status=last.status if last else None,
                last_delivery_at=last.created_at if last else None,
            )
        )
    return MasterWebhookListResponse(webhooks=out)


# ---------- Internal cron endpoint ----------

@internal_router.post("/process-retries", response_model=CronProcessRetriesResponse)
async def process_retries(
    request: Request,
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    db: Session = Depends(get_db),
):
    """Cron-driven retry processor. Auth is a shared secret in X-Internal-Secret.
    Unauthenticated requests get 404 to keep the endpoint invisible to scanners."""
    expected = settings.INTERNAL_CRON_SECRET
    if not expected or not x_internal_secret or not hmac.compare_digest(
        x_internal_secret.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    processed = WebhookService(db).process_pending_retries(batch_size=50)
    return CronProcessRetriesResponse(processed=processed)
