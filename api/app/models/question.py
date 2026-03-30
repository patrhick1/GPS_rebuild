import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)  # English question text
    question_es = Column(Text, nullable=True)  # Spanish translation
    order = Column(Integer, nullable=False)  # Display sequence
    passion_type = Column(String(255), nullable=True)  # Sub-categorization
    passion_type_es = Column(String(255), nullable=True)  # Spanish translation
    default_text = Column(Text, nullable=True)  # Default/placeholder text
    default_text_es = Column(Text, nullable=True)  # Spanish default
    summary = Column(Text, nullable=True)
    summary_es = Column(Text, nullable=True)
    type_id = Column(UUID(as_uuid=True), ForeignKey("types.id"), nullable=False)
    question_type_id = Column(UUID(as_uuid=True), ForeignKey("question_types.id"), nullable=False)
    instrument_type = Column(String(20), nullable=False, default="gps")  # gps, myimpact
    section = Column(String(50), nullable=True)  # For MyImpact: Character, Calling
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    type = relationship("Type", back_populates="questions")
    question_type = relationship("QuestionType", back_populates="questions")
    answers = relationship("Answer", back_populates="question")
