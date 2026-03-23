from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    preferred_instrument: Optional[str] = None


class OrganizationInDB(OrganizationBase):
    id: uuid.UUID
    key: str
    package: Optional[str] = None
    preferred_instrument: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    key: str
    preferred_instrument: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationWithStats(OrganizationResponse):
    member_count: int = 0
    admin_count: int = 0
    assessment_count: int = 0
