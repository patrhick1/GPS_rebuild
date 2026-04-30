import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class WebhookEvent(Base):
    """Idempotency record for processed Stripe webhook events.

    Stripe retries delivery on any non-2xx response and occasionally
    delivers duplicates. The webhook handler INSERTs into this table
    with ON CONFLICT DO NOTHING — if the row already exists, the
    event has already been processed and the handler returns 200
    immediately without re-running.
    """

    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id = Column(String(255), nullable=False, unique=True)
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
