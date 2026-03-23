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
        """Returns the 19 spiritual gifts from the GPS assessment (matching Laravel)."""
        return [
            {
                "name": "Administration",
                "short_code": "AD",
                "description": "Also called the gift of organization, this is the ability to organize and manage resources for effective ministry, and coordinate many details to execute the plans of leadership. It includes the ability to recognize the gifts of others, invite them to share their gifts, and serve them in their ministry efforts.",
                "questions": "9,28,47,66",
            },
            {
                "name": "Apostleship",
                "short_code": "AP",
                "description": "The ability to start new churches or mission efforts and oversee their development.",
                "questions": "14,33,52,71",
            },
            {
                "name": "Craftsmanship",
                "short_code": "C",
                "description": "The ability to creatively design and/or construct items to be used for ministry.",
                "questions": "16,35,54,73",
            },
            {
                "name": "Creative Communication",
                "short_code": "CC",
                "description": "The divine ability to communicate the truth of God through a variety of art forms.",
                "questions": "17,36,55,74",
            },
            {
                "name": "Discernment",
                "short_code": "D",
                "description": "The ability to distinguish right from wrong, truth from error, and to provide clear judgments based on God's Word. The ability to discern whether the source of a given experience is God's Spirit, self, or the enemy.",
                "questions": "13,32,51,70",
            },
            {
                "name": "Encouragement",
                "short_code": "EN",
                "description": "The ability to motivate God's people to apply and act on Biblical principles, including times when they are discouraged or wavering in their faith. The ability to bring out the best in others and challenge them to develop their full and challenge them to develop to their full potential.",
                "questions": "4,23,42,61",
            },
            {
                "name": "Evangelism",
                "short_code": "EV",
                "description": "The ability to share the Good News of Jesus Christ in a positive, sensitive, and effective way. The ability to sense and make the most of opportunities to share Jesus, and invite people to follow Him.",
                "questions": "1,20,39,58",
            },
            {
                "name": "Faith",
                "short_code": "F",
                "description": "The ability to trust God for what cannot be seen and to act on God's promise, regardless of what the circumstances indicate. It includes the willingness to risk failure in pursuit of a God-given vision, expecting God to handle the obstacles.",
                "questions": "18,37,56,75",
            },
            {
                "name": "Giving",
                "short_code": "G",
                "description": "The ability to generously and joyfully contribute material resources to strengthen and grow the church. The ability to earn and manage money so it may be given to support the ministry of others.",
                "questions": "8,27,46,65",
            },
            {
                "name": "Hospitality",
                "short_code": "H",
                "description": "The ability to make others, especially strangers, feel warmly welcomed, accepted, and comfortable in the church family. The ability to create events and environments that promote friendship.",
                "questions": "19,38,57,76",
            },
            {
                "name": "Intercession",
                "short_code": "I",
                "description": "The ability to pray for the needs of others in the church family over extended periods of time on a regular basis. The ability to persist in prayer and not be discouraged in awaiting answers.",
                "questions": "15,34,53,72",
            },
            {
                "name": "Knowledge",
                "short_code": "K",
                "description": "The ability to discern and analyze information that is vital to individual believers or the entire church family. The ability to grasp and interpret God's revelation with sound judgment.",
                "questions": "12,31,50,69",
            },
            {
                "name": "Leadership",
                "short_code": "L",
                "description": "The ability to clarify and communicate ministry purposes and goals in a way that attracts others to get involved and follow. The ability to motivate and organize others to work together in accomplishing a ministry goal.",
                "questions": "10,29,48,67",
            },
            {
                "name": "Mercy",
                "short_code": "ME",
                "description": "The ability to perceive when someone is suffering, and to empathize and help them. The ability to provide compassionate and cheerful support to those experiencing distress, crisis, or pain.",
                "questions": "6,25,44,63",
            },
            {
                "name": "Prophecy",
                "short_code": "PR",
                "description": "The ability to publicly communicate God's word in an inspired way that convinces unbelievers, and both challenges and comforts believers. The ability to accurately and persuasively declare God's will.",
                "questions": "2,21,40,59",
            },
            {
                "name": "Service",
                "short_code": "SE",
                "description": "The ability to recognize unmet needs in the church family, and take the initiative to provide practical assistance quickly, cheerfully, and without a need for recognition.",
                "questions": "7,26,45,64",
            },
            {
                "name": "Shepherding",
                "short_code": "SH",
                "description": "The ability to care for the spiritual needs of a group of believers and equip them for ministry. The ability to nurture a group toward spiritual growth and assume responsibility for their welfare.",
                "questions": "5,24,43,62",
            },
            {
                "name": "Teaching",
                "short_code": "TE",
                "description": "The ability to effectively and enthusiastically help others grow through the use of God's word. The ability to equip and train believers for ministry.",
                "questions": "3,22,41,60",
            },
            {
                "name": "Wisdom",
                "short_code": "W",
                "description": "The God given ability to hear the Holy Spirit and receive insights into what to do or to say to assist specific needs of God's family.",
                "questions": "11,30,49,68",
            },
        ]

    @staticmethod
    def get_default_influencing_styles():
        """Returns the 5 influencing styles from the GPS assessment (matching Laravel)."""
        return [
            {
                "name": "Apostle",
                "short_code": "A",
                "description": "Apostles extend the ministry of Jesus. Apostles are always thinking of ways to extend the ministry of Jesus beyond its current boundaries.",
                "questions": "5,10,15,20,25,30,35,40,45,50,55,60,64,65,70,73,75,80",
            },
            {
                "name": "Prophet",
                "short_code": "P",
                "description": "Prophets know and communicate God's will. Prophets keep us true to God's mission and purposes, particularly in light of current cultural trends.",
                "questions": "4,9,14,19,24,29,34,39,44,49,54,59,63,64,69,74,77,79",
            },
            {
                "name": "Evangelist",
                "short_code": "E",
                "description": "Evangelists recruit people to the mission. Evangelists invite people to accept redemption through Jesus, and motivate believers to develop their character and calling.",
                "questions": "3,8,13,18,21,23,28,33,38,43,48,53,58,63,68,72,73,78",
            },
            {
                "name": "Shepherd",
                "short_code": "S",
                "description": "Shepherds care for people and communities. Shepherds protect Jesus' 'sheep' and cultivate communities where the sheep can grow and be supported.",
                "questions": "1,6,8,11,16,21,23,26,31,36,41,46,51,56,61,66,71,76",
            },
            {
                "name": "Teacher",
                "short_code": "T",
                "description": "Teachers make God's word accessible to all. Teachers provide biblical training for making disciples and ensuring faithfulness to God's word in every facet of the church.",
                "questions": "2,7,11,6,12,17,22,27,32,37,42,47,52,57,61,62,67,72",
            },
        ]
