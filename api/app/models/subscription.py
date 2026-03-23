import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)  # Subscription name/plan
    stripe_id = Column(String(255), nullable=False)  # Stripe subscription ID
    stripe_status = Column(String(255), nullable=False)  # active, canceled, past_due, etc.
    stripe_plan = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)  # Cancellation effective date
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
