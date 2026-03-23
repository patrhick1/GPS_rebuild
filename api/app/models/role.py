import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)  # user, member, admin, master
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    memberships = relationship("Membership", back_populates="role")

    @staticmethod
    def get_default_roles():
        return [
            {"name": "user", "description": "Independent user, no church affiliation"},
            {"name": "member", "description": "Church member with affiliated organization"},
            {"name": "admin", "description": "Church administrator"},
            {"name": "master", "description": "System administrator with full access"},
        ]
