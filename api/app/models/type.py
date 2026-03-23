import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Type(Base):
    __tablename__ = "types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)  # "Spiritual Gift", "Influencing Style"
    description = Column(Text, nullable=True)
    order = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    gifts_passions = relationship("GiftsPassion", back_populates="type")
    questions = relationship("Question", back_populates="type")

    @staticmethod
    def get_default_types():
        return [
            {"name": "Spiritual Gift", "description": "Spiritual gifts assessment", "order": 1},
            {"name": "Influencing Style", "description": "Influencing style assessment", "order": 2},
            {"name": "Story", "description": "Story/free text questions", "order": 3},
        ]
