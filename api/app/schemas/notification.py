from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import uuid


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: str
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int
