import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=True)
    phone_number = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)
    locale = Column(String(10), nullable=False, default="en")
    status = Column(String(20), nullable=False, default="active")  # active, invited, locked, deleted
    stripe_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="user", cascade="all, delete-orphan")
    answers = relationship("Answer", back_populates="user", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="user", foreign_keys="Invitation.created_by")
    audit_logs = relationship("AuditLog", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    myimpact_results = relationship("MyImpactResult", back_populates="user")

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email
