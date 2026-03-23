"""
Dashboard schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid


# Summary schemas
class UserSummary(BaseModel):
    id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str


class GiftSummary(BaseModel):
    id: uuid.UUID
    name: str
    short_code: str
    score: int
    description: str


class PassionSummary(BaseModel):
    id: uuid.UUID
    name: str
    short_code: str
    score: int
    description: str


class LatestAssessment(BaseModel):
    id: uuid.UUID
    completed_at: datetime
    top_gifts: Optional[List[GiftSummary]] = None
    top_passions: Optional[List[PassionSummary]] = None


class UserStats(BaseModel):
    total_assessments: int
    has_organization: bool


class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    role: Optional[str] = None


class DashboardSummary(BaseModel):
    user: UserSummary
    latest_assessment: Optional[LatestAssessment] = None
    stats: UserStats
    organization: Optional[OrganizationSummary] = None


# History schemas
class GiftHistoryItem(BaseModel):
    name: str
    score: int


class PassionHistoryItem(BaseModel):
    name: str
    score: int


class AssessmentHistoryItem(BaseModel):
    id: uuid.UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    top_gifts: List[GiftHistoryItem] = []
    top_passions: List[PassionHistoryItem] = []


# Detail schemas
class GiftDetail(BaseModel):
    id: uuid.UUID
    name: str
    short_code: str
    score: int


class PassionDetail(BaseModel):
    id: uuid.UUID
    name: str
    short_code: str
    score: int


class Selections(BaseModel):
    people: List[str] = []
    causes: List[str] = []
    abilities: List[str] = []


class Stories(BaseModel):
    gift: Optional[str] = None
    ability: Optional[str] = None
    passion: Optional[str] = None
    influencing: Optional[str] = None
    onechange: Optional[str] = None
    closestpeople: Optional[str] = None
    oneregret: Optional[str] = None


class AssessmentDetail(BaseModel):
    id: uuid.UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    gifts: List[GiftDetail] = []
    passions: List[PassionDetail] = []
    selections: Selections
    stories: Stories


# Comparison schemas
class ComparisonRequest(BaseModel):
    assessment_id_1: uuid.UUID
    assessment_id_2: uuid.UUID


class ComparisonAssessment(BaseModel):
    id: uuid.UUID
    completed_at: Optional[datetime] = None
    gifts: List[GiftDetail] = []
    passions: List[PassionDetail] = []


class ComparisonResult(BaseModel):
    assessment_1: ComparisonAssessment
    assessment_2: ComparisonAssessment


# Church linking schemas
class ChurchSearchResult(BaseModel):
    id: uuid.UUID
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    member_count: int


class LinkRequestCreate(BaseModel):
    organization_id: uuid.UUID
    message: Optional[str] = None


class LinkRequestResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    status: str  # pending, approved, declined
    created_at: datetime
