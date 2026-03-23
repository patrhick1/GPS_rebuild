from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import uuid


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    sub: Optional[uuid.UUID] = None
    exp: Optional[datetime] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None
