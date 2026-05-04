import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, SmallInteger, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class WebhookDelivery(Base):
    """Append-only log of every webhook attempt.

    status:
      pending  — row created, no attempt yet
      success  — last attempt returned 2xx
      failed   — last attempt failed; more retries remain (next_retry_at set)
      dead     — max attempts exhausted (3); next_retry_at NULL

    The retry runner only picks up rows where status='failed' AND
    next_retry_at <= now AND attempts < 3.
    """

    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("webhook_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    http_status_code = Column(SmallInteger, nullable=True)
    error_message = Column(Text, nullable=True)
    attempts = Column(SmallInteger, nullable=False, default=0)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    config = relationship("WebhookConfig", back_populates="deliveries")

    __table_args__ = (
        Index("ix_webhook_deliveries_status_next_retry", "status", "next_retry_at"),
        Index("ix_webhook_deliveries_config_created", "webhook_config_id", "created_at"),
    )
