import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(String(1), nullable=False, default="N")  # Y or N
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
