from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limits import limiter, PUBLIC_AUTH_RATE, PASSWORD_RESET_RATE, AUTHENTICATED_RATE
from app.core.audit import log_audit_event
from app.dependencies.auth import get_current_user, get_current_active_user, get_current_active_user_no_impersonation
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserWithRole,
    UserUpdate,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChange,
    PasswordStrengthResponse,
    ChurchAdminRegister,
    ChurchUpgrade,
)
from app.core.password_policy import PasswordPolicy
from app.schemas.token import Token, RefreshTokenRequest
from app.services.auth_service import AuthService
from app.services.email_service import send_password_reset_email
from app.models.user import User
from app.models.membership import Membership
from app.models.organization import Organization

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(PUBLIC_AUTH_RATE)
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


@router.post("/upgrade/church", response_model=UserWithRole)
@limiter.limit(AUTHENTICATED_RATE)
async def upgrade_to_church_admin(
    request: Request,
    data: ChurchUpgrade,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upgrade an existing logged-in user to church admin."""
    auth_service = AuthService(db)
    user = auth_service.upgrade_to_church_admin(current_user, data)

    log_audit_event(
        db=db,
        user_id=user.id,
        action="upgraded_to_church_admin",
        target_type="user",
        target_id=str(user.id),
        details={"org_name": data.org_name}
    )

    # Return fresh user+role data so frontend can update immediately
    membership = db.query(Membership).filter(Membership.user_id == user.id).first()
    result = UserWithRole.model_validate(user)
    if membership:
        result.role = membership.role.name if membership.role else None
        result.organization_id = membership.organization_id
        result.is_primary_admin = membership.is_primary_admin
        if membership.organization:
            result.organization_name = membership.organization.name
    return result


@router.post("/register/church", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(PUBLIC_AUTH_RATE)
async def register_church(
    request: Request,
    data: ChurchAdminRegister,
    db: Session = Depends(get_db),
):
    """Register a new church admin account with organization."""
    auth_service = AuthService(db)
    user = auth_service.register_church_admin(data)
    return user


@router.post("/login", response_model=Token)
@limiter.limit(PUBLIC_AUTH_RATE)
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
        # Log failed login attempt
        log_audit_event(
            db=db,
            user_id=None,
            action="login_failed",
            target_type="user",
            target_id=None,
            details={
                "email": login_data.email,
                "reason": "invalid_credentials",
                "ip_address": request.client.host if request.client else None
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status == "locked":
        # Log failed login attempt for locked account
        log_audit_event(
            db=db,
            user_id=user.id,
            action="login_failed",
            target_type="user",
            target_id=str(user.id),
            details={
                "reason": "account_locked",
                "ip_address": request.client.host if request.client else None
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked",
        )
    
    # Log successful login
    log_audit_event(
        db=db,
        user_id=user.id,
        action="login_success",
        target_type="user",
        target_id=str(user.id),
        details={
            "ip_address": request.client.host if request.client else None
        }
    )
    
    tokens = auth_service.create_tokens(user.id)

    # In production the frontend and API are on different onrender.com subdomains
    # (cross-site per Public Suffix List), so cookies must be SameSite=None;Secure.
    # In local dev both run on localhost (same-site), so Lax + non-Secure is fine.
    cookie_samesite = "lax" if settings.DEBUG else "none"
    cookie_secure = not settings.DEBUG

    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    # Also set access token cookie for convenience
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return Token(**tokens)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Refresh access token using httpOnly refresh_token cookie."""
    refresh_token_str = request.cookies.get("refresh_token")
    
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    
    auth_service = AuthService(db)
    tokens = auth_service.refresh_access_token(refresh_token_str)
    
    cookie_samesite = "lax" if settings.DEBUG else "none"
    cookie_secure = not settings.DEBUG

    # Update cookies
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
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
    
    cookie_samesite = "lax" if settings.DEBUG else "none"
    cookie_secure = not settings.DEBUG

    # Clear cookies — must match the same Secure/SameSite attributes used when setting them
    response.delete_cookie("access_token", secure=cookie_secure, samesite=cookie_samesite)
    response.delete_cookie("refresh_token", secure=cookie_secure, samesite=cookie_samesite)
    
    return {"message": "Successfully logged out"}


@router.post("/password-reset-request")
@limiter.limit(PASSWORD_RESET_RATE)
async def password_reset_request(
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request a password reset email."""
    auth_service = AuthService(db)
    token = auth_service.create_password_reset_token(reset_request.email)

    # Only send if user exists; always return same message (security)
    if token:
        send_password_reset_email(to_email=reset_request.email, reset_token=token)

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
    current_user: User = Depends(get_current_active_user_no_impersonation),
    db: Session = Depends(get_db),
):
    """
    Change password for authenticated user.
    
    Note: Impersonation tokens cannot be used to change passwords.
    This prevents master admins from accidentally or maliciously changing
    user passwords during impersonation sessions.
    """
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
    
    # Log password change
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="password_changed",
        target_type="user",
        target_id=str(current_user.id)
    )
    
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserWithRole)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get current authenticated user with role information."""
    membership = current_user.memberships[0] if current_user.memberships else None

    result = UserWithRole.model_validate(current_user)
    if membership:
        result.role = membership.role.name if membership.role else None
        result.organization_id = membership.organization_id
        result.is_primary_admin = membership.is_primary_admin
        if membership.organization:
            result.organization_name = membership.organization.name
    return result


@router.put("/profile", response_model=UserResponse)
@limiter.limit(AUTHENTICATED_RATE)
async def update_profile(
    request: Request,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update profile for the current authenticated user."""
    update_fields = user_data.model_dump(exclude_none=True)

    for field, value in update_fields.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/org/{org_key}")
async def get_org_by_key(org_key: str, db: Session = Depends(get_db)):
    """Return public org info for the registration page church-link flow."""
    org = db.query(Organization).filter(
        Organization.key == org_key,
        Organization.status == "active",
    ).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return {"name": org.name, "city": org.city, "state": org.state}


@router.post("/password-strength", response_model=PasswordStrengthResponse)
async def check_password_strength(
    password: str = Form(...),
    email: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form("")
):
    """
    Check password strength and validate against policy.
    
    This endpoint is public and can be called during registration
    to provide real-time password strength feedback.
    """
    score = PasswordPolicy.calculate_strength(password)
    label, color = PasswordPolicy.get_strength_label(score)
    is_valid, errors = PasswordPolicy.validate(
        password=password,
        email=email if email else None,
        first_name=first_name if first_name else None,
        last_name=last_name if last_name else None
    )
    
    return PasswordStrengthResponse(
        score=score,
        strength_label=label,
        color=color,
        is_valid=is_valid,
        errors=errors,
        requirements=PasswordPolicy.get_requirements_description()
    )
