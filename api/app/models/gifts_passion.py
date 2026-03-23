import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class GiftsPassion(Base):
    __tablename__ = "gifts_passions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)  # e.g., "Administration", "Apostle", "Teacher"
    short_code = Column(String(5), nullable=False, unique=True)  # e.g., "AD", "AP", "TE"
    description = Column(Text, nullable=False)
    questions = Column(Text, nullable=False)  # Comma-separated question IDs
    type_id = Column(UUID(as_uuid=True), ForeignKey("types.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    type = relationship("Type", back_populates="gifts_passions")

    @staticmethod
    def get_default_gifts():
        """Returns the 19 spiritual gifts from the GPS assessment."""
        return [
            {"name": "Administration", "short_code": "AD", "description": "The gift of administration is the divine enablement to understand what makes an organization function and the special ability to plan and execute procedures that increase the church's organizational efficiency."},
            {"name": "Apostleship", "short_code": "AP", "description": "The gift of apostleship is the divine enablement to start and oversee the development of new churches or ministry structures."},
            {"name": "Craftsmanship", "short_code": "CR", "description": "The gift of craftsmanship is the divine enablement to creatively design and/or construct items to be used for ministry."},
            {"name": "Discernment", "short_code": "DI", "description": "The gift of discernment is the divine enablement to distinguish between truth and error, to discern the spirits, differentiating between good and evil, right and wrong."},
            {"name": "Evangelism", "short_code": "EV", "description": "The gift of evangelism is the divine enablement to effectively communicate the gospel to unbelievers and bring them to a saving knowledge of Christ."},
            {"name": "Exhortation", "short_code": "EX", "description": "The gift of exhortation is the divine enablement to encourage, comfort, and challenge others through the spoken or written word."},
            {"name": "Faith", "short_code": "FA", "description": "The gift of faith is the divine enablement to believe God for what is needed to accomplish His purposes."},
            {"name": "Giving", "short_code": "GI", "description": "The gift of giving is the divine enablement to contribute material resources to the work of the Lord with liberality and cheerfulness."},
            {"name": "Healing", "short_code": "HE", "description": "The gift of healing is the divine enablement to be used as a means for healing various kinds of illnesses."},
            {"name": "Helps", "short_code": "HL", "description": "The gift of helps is the divine enablement to accomplish practical and necessary tasks that free-up, support, and meet the needs of others."},
            {"name": "Hospitality", "short_code": "HO", "description": "The gift of hospitality is the divine enablement to care for people by providing fellowship, food, and shelter."},
            {"name": "Knowledge", "short_code": "KN", "description": "The gift of knowledge is the divine enablement to discover, analyze, and systematize truth for the benefit of others."},
            {"name": "Leadership", "short_code": "LE", "description": "The gift of leadership is the divine enablement to cast vision, motivate, and direct people to harmoniously accomplish the purposes of God."},
            {"name": "Mercy", "short_code": "ME", "description": "The gift of mercy is the divine enablement to feel empathy and compassion for those who are suffering physically, mentally, or emotionally."},
            {"name": "Miracles", "short_code": "MI", "description": "The gift of miracles is the divine enablement to authenticate the ministry and message of God through supernatural interventions."},
            {"name": "Prophecy", "short_code": "PR", "description": "The gift of prophecy is the divine enablement to proclaim divine truth with clarity and authority."},
            {"name": "Shepherding", "short_code": "SH", "description": "The gift of shepherding is the divine enablement to nurture and guide others toward spiritual maturity."},
            {"name": "Teaching", "short_code": "TE", "description": "The gift of teaching is the divine enablement to understand and communicate biblical truth in a clear and relevant manner."},
            {"name": "Wisdom", "short_code": "WI", "description": "The gift of wisdom is the divine enablement to apply spiritual truth to specific situations in the most effective way."},
        ]

    @staticmethod
    def get_default_influencing_styles():
        """Returns the 5 influencing styles from the GPS assessment."""
        return [
            {"name": "Advocate", "short_code": "ADV", "description": "Advocates are passionate about causes and work to influence others through conviction and dedication to specific issues."},
            {"name": "Apostle", "short_code": "APS", "description": "Apostles are pioneers who go before others, establishing new works and breaking new ground."},
            {"name": "Prophet", "short_code": "PRO", "description": "Prophets are truth-tellers who speak with authority and challenge the status quo."},
            {"name": "Teacher", "short_code": "TCH", "description": "Teachers are explainers who help others understand complex ideas through clear instruction."},
            {"name": "Storyteller", "short_code": "STO", "description": "Storytellers are communicators who influence through narrative and personal experience."},
        ]
