"""
Admin schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import uuid


# Member schemas
class MemberDetail(BaseModel):
    id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    status: str
    role: Optional[str] = None
    joined_at: datetime
    assessment_count: int
    last_assessment_date: Optional[datetime] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    members: List[MemberDetail]
    total: int
    page: int
    per_page: int
    total_pages: int


class MemberUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None


# Invite schemas
class InviteCreate(BaseModel):
    email: str


class InviteResponse(BaseModel):
    id: uuid.UUID
    email: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InviteListResponse(BaseModel):
    invites: List[InviteResponse]


class BulkInviteRequest(BaseModel):
    emails: List[str]


class FailedInvite(BaseModel):
    email: str
    reason: str


class BulkInviteResponse(BaseModel):
    created_count: int
    created_emails: List[str]
    failed: List[FailedInvite]


# Pending member schemas
class PendingMember(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    requested_at: datetime


# Church settings schemas
class ChurchSettings(BaseModel):
    id: uuid.UUID
    name: str
    key: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    preferred_instrument: Optional[str] = None


class ChurchStats(BaseModel):
    total_members: int
    active_members: int
    pending_members: int
    total_assessments: int
