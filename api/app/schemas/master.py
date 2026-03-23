"""
Master Admin schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid


# System Stats
class TimeRangeStats(BaseModel):
    new_users: int
    assessments: int


class SystemStats(BaseModel):
    total_users: int
    total_churches: int
    total_assessments: int
    active_churches: int
    recent_stats: Dict[str, TimeRangeStats]


# Church schemas
class ChurchAdmin(BaseModel):
    id: uuid.UUID
    email: str
    name: str


class ChurchDetail(BaseModel):
    id: uuid.UUID
    name: str
    key: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    member_count: int
    assessment_count: int
    admins: List[ChurchAdmin]
    last_activity: Optional[datetime] = None
    created_at: datetime


class ChurchListResponse(BaseModel):
    churches: List[ChurchDetail]
    total: int
    page: int
    per_page: int
    total_pages: int


# User schemas
class UserOrganization(BaseModel):
    id: uuid.UUID
    name: str
    role: Optional[str] = None


class UserDetail(BaseModel):
    id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    status: str
    organization: Optional[UserOrganization] = None
    assessment_count: int
    created_at: datetime
    last_login: Optional[datetime] = None


class UserListResponse(BaseModel):
    users: List[UserDetail]
    total: int
    page: int
    per_page: int
    total_pages: int


# Audit Log schemas
class AuditLogEntry(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[uuid.UUID] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    entries: List[AuditLogEntry]
    total: int
    page: int
    per_page: int
    total_pages: int


# Impersonation schemas
class ImpersonateRequest(BaseModel):
    user_id: uuid.UUID
    reason: str


class ImpersonateResponse(BaseModel):
    token: str
    user_id: uuid.UUID
    email: str
    message: str


# Export schemas
class SystemExportRequest(BaseModel):
    export_type: str  # users, assessments, churches
    organization_id: Optional[uuid.UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
