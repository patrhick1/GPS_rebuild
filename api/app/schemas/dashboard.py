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
    # Surfaced in the "currently linked" banner so members can tell apart
    # same-named churches in different locations (Sherri 2026-06-16).
    city: Optional[str] = None
    state: Optional[str] = None


class PendingOrganization(BaseModel):
    """Shown when user has a pending or declined membership request."""
    id: uuid.UUID
    name: str
    status: str  # "pending" or "declined"


class DashboardSummary(BaseModel):
    user: UserSummary
    latest_assessment: Optional[LatestAssessment] = None
    stats: UserStats
    organization: Optional[OrganizationSummary] = None
    pending_organization: Optional[PendingOrganization] = None


# History schemas
class GiftHistoryItem(BaseModel):
    name: str
    short_code: str
    score: int


class PassionHistoryItem(BaseModel):
    name: str
    short_code: str
    score: int


class AssessmentHistoryItem(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID
    status: str
    instrument_type: str = "gps"
    completed_at: Optional[datetime] = None
    created_at: datetime
    progress_percentage: int
    top_gifts: List[GiftHistoryItem] = []
    top_passions: List[PassionHistoryItem] = []
    # MyImpact fields
    myimpact_score: Optional[float] = None
    character_score: Optional[float] = None
    calling_score: Optional[float] = None


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


class ComparisonMyImpactAssessment(BaseModel):
    """Shape returned by /dashboard/compare when both assessments are
    MyImpact. Character / calling dicts are keyed by dimension name
    (matches MyImpactResult.get_character_breakdown / get_calling_breakdown)
    so the frontend can resolve labels via the same i18n map it already
    uses on the results page."""
    id: uuid.UUID
    completed_at: Optional[datetime] = None
    character: dict = {}
    calling: dict = {}
    character_score: Optional[float] = None
    calling_score: Optional[float] = None
    myimpact_score: Optional[float] = None


class ComparisonResult(BaseModel):
    # New discriminator field defaulted to "gps" so existing clients that
    # never read it continue to render GPS comparisons correctly.
    instrument_type: str = "gps"
    # GPS shape (populated when instrument_type == "gps")
    assessment_1: Optional[ComparisonAssessment] = None
    assessment_2: Optional[ComparisonAssessment] = None
    # MyImpact shape (populated when instrument_type == "myimpact")
    myimpact_1: Optional[ComparisonMyImpactAssessment] = None
    myimpact_2: Optional[ComparisonMyImpactAssessment] = None


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
