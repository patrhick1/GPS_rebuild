from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
import uuid


# Base User schema
class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    locale: str = "en"


# Schema for creating a user (registration)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    organization_key: Optional[str] = None  # For church-specific registration


# Schema for updating a user
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    locale: Optional[str] = None


# Schema for user in database
class UserInDB(UserBase):
    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Schema for user response (public)
class UserResponse(UserBase):
    id: uuid.UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Schema for user with role information
class UserWithRole(UserResponse):
    role: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    organization_name: Optional[str] = None


# Schema for login request
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Schema for password reset request
class PasswordResetRequest(BaseModel):
    email: EmailStr


# Schema for password reset confirmation
class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# Schema for change password
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
