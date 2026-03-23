from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_active_user
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChange,
)
from app.schemas.token import Token, RefreshTokenRequest
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    auth_service = AuthService(db)
    user = auth_service.register_user(
        user_data=user_data,
        organization_key=user_data.organization_key,
    )
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    """Authenticate user and return tokens."""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(login_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status == "locked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked",
        )
    
    tokens = auth_service.create_tokens(user.id)
    
    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    
    # Also set access token cookie for convenience
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return Token(**tokens)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    token_data: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token."""
    # Try to get refresh token from body or cookie
    refresh_token_str = None
    if token_data:
        refresh_token_str = token_data.refresh_token
    if not refresh_token_str:
        refresh_token_str = request.cookies.get("refresh_token")
    
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    
    auth_service = AuthService(db)
    tokens = auth_service.refresh_access_token(refresh_token_str)
    
    # Update cookies
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return Token(**tokens)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token_data: RefreshTokenRequest | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Logout user and revoke refresh token."""
    refresh_token_str = None
    if token_data:
        refresh_token_str = token_data.refresh_token
    if not refresh_token_str:
        refresh_token_str = request.cookies.get("refresh_token")
    
    if refresh_token_str:
        auth_service = AuthService(db)
        auth_service.revoke_refresh_token(refresh_token_str)
    
    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Successfully logged out"}


@router.post("/password-reset-request")
@limiter.limit("3/minute")
async def password_reset_request(
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request a password reset email."""
    auth_service = AuthService(db)
    token = auth_service.create_password_reset_token(reset_request.email)
    
    # TODO: Send email with reset link using Resend
    # For now, just return success even if email doesn't exist (security)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset")
async def password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Reset password using reset token."""
    auth_service = AuthService(db)
    success = auth_service.reset_password(reset_data.token, reset_data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change password for authenticated user."""
    auth_service = AuthService(db)
    success = auth_service.change_password(
        current_user.id,
        password_data.current_password,
        password_data.new_password,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current authenticated user."""
    return current_user
