import uuid
from datetime import datetime
from sqlalchemy import Column, SmallInteger, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Spiritual Gifts (top 4 with scores)
    gift_1_id = Column(UUID(as_uuid=True), ForeignKey("gifts_passions.id"), nullable=True)
    spiritual_gift_1_score = Column(SmallInteger, nullable=True)
    gift_2_id = Column(UUID(as_uuid=True), ForeignKey("gifts_passions.id"), nullable=True)
    spiritual_gift_2_score = Column(SmallInteger, nullable=True)
    gift_3_id = Column(UUID(as_uuid=True), ForeignKey("gifts_passions.id"), nullable=True)
    spiritual_gift_3_score = Column(SmallInteger, nullable=True)
    gift_4_id = Column(UUID(as_uuid=True), ForeignKey("gifts_passions.id"), nullable=True)
    spiritual_gift_4_score = Column(SmallInteger, nullable=True)
    
    # Influencing Styles (top 3 with scores)
    passion_1_id = Column(UUID(as_uuid=True), ForeignKey("gifts_passions.id"), nullable=True)
    passion_1_score = Column(SmallInteger, nullable=True)
    passion_2_id = Column(UUID(as_uuid=True), ForeignKey("gifts_passions.id"), nullable=True)
    passion_2_score = Column(SmallInteger, nullable=True)
    passion_3_id = Column(UUID(as_uuid=True), ForeignKey("gifts_passions.id"), nullable=True)
    passion_3_score = Column(SmallInteger, nullable=True)
    
    # Story responses
    people = Column(Text, nullable=True)
    cause = Column(Text, nullable=True)
    abilities = Column(Text, nullable=True)
    story_gift_answer = Column(Text, nullable=True)
    story_ability_answer = Column(Text, nullable=True)
    story_passion_answer = Column(Text, nullable=True)
    story_influencing_answer = Column(Text, nullable=True)
    story_onechange_answer = Column(Text, nullable=True)
    story_closestpeople_answer = Column(Text, nullable=True)
    story_oneregret_answer = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="results")
