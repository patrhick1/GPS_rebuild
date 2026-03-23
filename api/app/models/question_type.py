import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class QuestionType(Base):
    __tablename__ = "question_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(100), nullable=False, unique=True)  # likert, multiple_choice, text
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    questions = relationship("Question", back_populates="question_type")

    @staticmethod
    def get_default_types():
        return [
            {"type": "likert", "description": "1-5 rating scale questions"},
            {"type": "multiple_choice", "description": "Selection from predefined options"},
            {"type": "text", "description": "Free text response"},
        ]
