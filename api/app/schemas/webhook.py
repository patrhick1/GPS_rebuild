"""Pydantic schemas for webhook config + delivery API."""
from datetime import datetime
from typing import List, Literal, Optional
import uuid

from pydantic import BaseModel, Field, HttpUrl


WebhookEventType = Literal["assessment_completed", "user_registered"]


class WebhookConfigCreate(BaseModel):
    webhook_url: HttpUrl
    event_type: WebhookEventType
    is_active: bool = True
    generate_secret: bool = False


class WebhookConfigUpdate(BaseModel):
    webhook_url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None
    generate_secret: Optional[bool] = None
    """If True, regenerates the signing secret. Returned masked thereafter."""


class WebhookConfigResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    event_type: str
    webhook_url: str
    is_active: bool
    has_secret: bool
    secret_masked: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookConfigCreatedResponse(WebhookConfigResponse):
    """Returned only on create / regenerate; secret_plaintext is shown once."""
    secret_plaintext: Optional[str] = None


class WebhookConfigListResponse(BaseModel):
    webhooks: List[WebhookConfigResponse]


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    webhook_config_id: uuid.UUID
    event_type: str
    status: str
    http_status_code: Optional[int] = None
    error_message: Optional[str] = None
    attempts: int
    next_retry_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryListResponse(BaseModel):
    deliveries: List[WebhookDeliveryResponse]
    total_count: int


class WebhookTestResponse(BaseModel):
    ok: bool
    status_code: Optional[int] = None
    error: Optional[str] = None


class MasterWebhookConfigResponse(BaseModel):
    """Master admin read-only view; URL masked, no secret exposure."""
    id: uuid.UUID
    organization_id: uuid.UUID
    event_type: str
    webhook_url_masked: str
    is_active: bool
    has_secret: bool
    last_delivery_status: Optional[str] = None
    last_delivery_at: Optional[datetime] = None


class MasterWebhookListResponse(BaseModel):
    webhooks: List[MasterWebhookConfigResponse]


class CronProcessRetriesResponse(BaseModel):
    processed: int = Field(..., description="Count of delivery rows redelivered this run.")
