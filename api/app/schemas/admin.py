"""
Admin schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import uuid


# Assessment summary schemas for member table pills
class GiftSummary(BaseModel):
    name: str
    short_code: str
    score: int


class PassionSummary(BaseModel):
    name: str
    short_code: str
    score: int


# Member schemas
class MemberDetail(BaseModel):
    id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    status: str
    role: Optional[str] = None
    is_admin: bool = False
    is_primary_admin: bool = False
    joined_at: datetime
    assessment_count: int
    last_assessment_date: Optional[datetime] = None
    latest_gps_assessment_id: Optional[uuid.UUID] = None
    latest_myimpact_assessment_id: Optional[uuid.UUID] = None
    phone_number: Optional[str] = None
    top_gifts: List[GiftSummary] = []
    top_passions: List[PassionSummary] = []
    myimpact_character_score: Optional[float] = None
    myimpact_calling_score: Optional[float] = None
    myimpact_score: Optional[float] = None

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


class TransferPrimaryAdminRequest(BaseModel):
    target_member_id: str


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
    gps_assessments: int = 0
    myimpact_assessments: int = 0
    avg_character_score: Optional[float] = None
    avg_calling_score: Optional[float] = None
    avg_myimpact_score: Optional[float] = None
