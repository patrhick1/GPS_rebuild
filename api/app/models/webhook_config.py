import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class WebhookConfig(Base):
    """Per-organization, per-event webhook destination configured by a church admin.

    One row per (organization_id, event_type). The event_type field is what lets
    Feature 2 (assessment_completed) and Feature 3 (user_registered) coexist
    on the same table without separate models.
    """

    __tablename__ = "webhook_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(50), nullable=False)  # assessment_completed | user_registered
    webhook_url = Column(String(2048), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    secret = Column(String(255), nullable=True)  # Optional HMAC-SHA256 signing secret
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    organization = relationship("Organization", backref="webhook_configs")
    deliveries = relationship(
        "WebhookDelivery",
        back_populates="config",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "event_type", name="uq_webhook_configs_org_event"),
        Index("ix_webhook_configs_org_active", "organization_id", "is_active"),
    )
