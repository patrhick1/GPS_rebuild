"""
MyImpact Assessment Result Model
Stores results for MyImpact assessments (Character × Calling)
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Float, SmallInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class MyImpactResult(Base):
    """
    Stores scored results for MyImpact assessments.
    
    MyImpact Score = Character Score × Calling Score
    Character Score = Average of 9 Fruit of the Spirit questions (1-10 scale)
    Calling Score = Average of 8 Calling questions (1-10 scale)
    Final Score Range: 1.0 - 100.0
    """
    __tablename__ = "myimpact_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Character Section - Fruit of the Spirit (9 questions)
    c1_loving = Column(SmallInteger, nullable=True)  # I am a loving person
    c2_joyful = Column(SmallInteger, nullable=True)  # I am a joyful person
    c3_peaceful = Column(SmallInteger, nullable=True)  # I am a peaceful person
    c4_patient = Column(SmallInteger, nullable=True)  # I am a patient person
    c5_kind = Column(SmallInteger, nullable=True)  # I am a kind person
    c6_good = Column(SmallInteger, nullable=True)  # I am a good person
    c7_faithful = Column(SmallInteger, nullable=True)  # I am a faithful person
    c8_gentle = Column(SmallInteger, nullable=True)  # I am a gentle person
    c9_self_controlled = Column(SmallInteger, nullable=True)  # I am a self-controlled person
    character_score = Column(Float, nullable=True)  # Average of C1-C9 (1.0-10.0)
    
    # Calling Section (8 questions)
    cl1_know_gifts = Column(SmallInteger, nullable=True)  # I can name my top 3 Spiritual Gifts
    cl2_know_people = Column(SmallInteger, nullable=True)  # I know the specific people/causes God wants me to serve
    cl3_using_gifts = Column(SmallInteger, nullable=True)  # I am currently using my gifts to serve
    cl4_see_impact = Column(SmallInteger, nullable=True)  # I regularly see God making a difference
    cl5_experience_joy = Column(SmallInteger, nullable=True)  # I experience significant joy serving
    cl6_pray_regularly = Column(SmallInteger, nullable=True)  # I regularly pray for people
    cl7_see_movement = Column(SmallInteger, nullable=True)  # I see people move from indifference to faith
    cl8_receive_support = Column(SmallInteger, nullable=True)  # I receive consistent support/encouragement
    calling_score = Column(Float, nullable=True)  # Average of CL1-CL8 (1.0-10.0)
    
    # Final MyImpact Score
    myimpact_score = Column(Float, nullable=True)  # character_score × calling_score (1.0-100.0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="myimpact_results")
    user = relationship("User", back_populates="myimpact_results")

    def get_character_breakdown(self):
        """Return character dimension scores as a dict."""
        return {
            "loving": self.c1_loving,
            "joyful": self.c2_joyful,
            "peaceful": self.c3_peaceful,
            "patient": self.c4_patient,
            "kind": self.c5_kind,
            "good": self.c6_good,
            "faithful": self.c7_faithful,
            "gentle": self.c8_gentle,
            "self_controlled": self.c9_self_controlled,
        }
    
    def get_calling_breakdown(self):
        """Return calling dimension scores as a dict."""
        return {
            "know_gifts": self.cl1_know_gifts,
            "know_people": self.cl2_know_people,
            "using_gifts": self.cl3_using_gifts,
            "see_impact": self.cl4_see_impact,
            "experience_joy": self.cl5_experience_joy,
            "pray_regularly": self.cl6_pray_regularly,
            "see_movement": self.cl7_see_movement,
            "receive_support": self.cl8_receive_support,
        }
