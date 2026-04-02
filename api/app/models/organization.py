import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    city = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)
    key = Column(String(255), nullable=False, unique=True)  # Slug for church-specific URLs
    package = Column(String(255), nullable=True)  # Subscription tier
    stripe_id = Column(String(255), nullable=True)
    card_brand = Column(String(255), nullable=True)
    card_last_four = Column(String(4), nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    preferred_instrument = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active, paused
    is_comped = Column(Boolean, nullable=False, default=False)  # True = billed elsewhere, bypass Stripe check
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    memberships = relationship("Membership", back_populates="organization")
    invitations = relationship("Invitation", back_populates="organization")
