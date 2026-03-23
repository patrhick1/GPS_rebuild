import uuid
from datetime import datetime
from sqlalchemy import Column, String, SmallInteger, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Answer(Base):
    __tablename__ = "answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    multiple_choice_answer = Column(String(255), nullable=True)
    numeric_value = Column(SmallInteger, nullable=True)  # 1-5 Likert scale
    text_value = Column(Text, nullable=True)  # Free text responses
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    user = relationship("User", back_populates="answers")
