from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid


class InvitationBase(BaseModel):
    email: EmailStr


class InvitationCreate(InvitationBase):
    organization_id: Optional[uuid.UUID] = None


class InvitationCreateBatch(BaseModel):
    emails: list[EmailStr]
    organization_id: Optional[uuid.UUID] = None


class InvitationInDB(InvitationBase):
    id: uuid.UUID
    sign_up_key: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    status: str
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationResponse(InvitationBase):
    id: uuid.UUID
    status: str
    organization_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationVerify(BaseModel):
    token: str


class InvitationAccept(BaseModel):
    token: str
    first_name: str
    last_name: str
    password: str
