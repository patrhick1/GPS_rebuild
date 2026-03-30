from datetime import datetime
from typing import Optional, List, Self
from pydantic import BaseModel, EmailStr, Field, model_validator
import uuid

from app.core.password_policy import PasswordPolicy


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
    
    @model_validator(mode='after')
    def validate_password_strength(self) -> Self:
        """Validate password against security policy."""
        is_valid, errors = PasswordPolicy.validate(
            password=self.password,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name
        )
        if not is_valid:
            raise ValueError(f"Password does not meet requirements: {'; '.join(errors)}")
        return self


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
    is_primary_admin: bool = False


# Schema for upgrading an existing user to church admin
class ChurchUpgrade(BaseModel):
    org_name: str
    org_city: Optional[str] = None
    org_state: Optional[str] = None
    org_country: Optional[str] = None


# Schema for church admin registration (new users only)
class ChurchAdminRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    org_name: str
    org_city: Optional[str] = None
    org_state: Optional[str] = None
    org_country: Optional[str] = None

    @model_validator(mode='after')
    def validate_password_strength(self) -> Self:
        is_valid, errors = PasswordPolicy.validate(
            password=self.password,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name
        )
        if not is_valid:
            raise ValueError(f"Password does not meet requirements: {'; '.join(errors)}")
        return self


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
    
    @model_validator(mode='after')
    def validate_password_strength(self) -> Self:
        """Validate new password against security policy."""
        is_valid, errors = PasswordPolicy.validate(password=self.new_password)
        if not is_valid:
            raise ValueError(f"Password does not meet requirements: {'; '.join(errors)}")
        return self


# Schema for change password
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @model_validator(mode='after')
    def validate_password_strength(self) -> Self:
        """Validate new password against security policy."""
        is_valid, errors = PasswordPolicy.validate(password=self.new_password)
        if not is_valid:
            raise ValueError(f"Password does not meet requirements: {'; '.join(errors)}")
        return self


# Schema for password strength check (for UI feedback)
class PasswordStrengthResponse(BaseModel):
    """Response schema for password strength calculation."""
    score: int  # 0-100
    strength_label: str  # Very Weak, Weak, Fair, Strong, Very Strong
    color: str  # CSS color class
    is_valid: bool
    errors: List[str]
    requirements: str  # Human-readable requirements description
