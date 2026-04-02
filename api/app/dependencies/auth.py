import uuid
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import desc
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token, verify_token_not_impersonation
from app.models.user import User
from app.models.role import Role
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.subscription import Subscription

# Statuses that grant full admin dashboard access (write operations)
_ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due"}

# Statuses that grant read-only admin view (expired but can still see historical data)
_VIEW_ALLOWED_STATUSES = {"active", "trialing", "past_due", "canceled", "unpaid"}

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    allow_impersonation: bool = True  # Allow impersonation by default, but can be disabled
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    Checks both Authorization header and cookie.
    
    Args:
        request: FastAPI request object
        credentials: HTTP Authorization credentials
        db: Database session
        allow_impersonation: If False, rejects impersonation tokens
    
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If authentication fails
    """
    token = None
    
    # Try to get token from Authorization header
    if credentials:
        token = credentials.credentials
    
    # If no token in header, try to get from cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if impersonation tokens are allowed for this endpoint
    if not allow_impersonation:
        is_valid, payload, error = verify_token_not_impersonation(token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error,
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload_to_use = payload
    else:
        payload_to_use = decode_token(token)
    
    if payload_to_use is None or payload_to_use.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str = payload_to_use.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert string user_id to UUID
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status in ["locked", "deleted"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    # Store token info in request state for access in endpoints
    request.state.is_impersonation = payload_to_use.get("impersonation", False)
    request.state.impersonated_by = payload_to_use.get("impersonated_by")
    request.state.impersonation_reason = payload_to_use.get("impersonation_reason")
    
    return user


async def get_current_user_no_impersonation(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user, but reject impersonation tokens.
    
    Use this for sensitive endpoints where impersonation should not be allowed,
    such as password changes, billing operations, or account deletion.
    """
    return await get_current_user(request, credentials, db, allow_impersonation=False)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to ensure user is active (not invited/pending)."""
    if current_user.status == "invited":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please complete your registration first",
        )
    return current_user


async def get_current_active_user_no_impersonation(
    current_user: User = Depends(get_current_user_no_impersonation)
) -> User:
    """Get current active user, rejecting impersonation tokens."""
    if current_user.status == "invited":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please complete your registration first",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin or master role."""
    # Check user's role through membership
    membership = current_user.memberships[0] if current_user.memberships else None
    if membership:
        role_name = membership.role.name if membership.role else None
        if role_name in ["admin", "master"]:
            return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


def require_admin_no_impersonation(
    current_user: User = Depends(get_current_user_no_impersonation)
) -> User:
    """Require admin role, rejecting impersonation tokens."""
    membership = current_user.memberships[0] if current_user.memberships else None
    if membership:
        role_name = membership.role.name if membership.role else None
        if role_name in ["admin", "master"]:
            return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


def require_master(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require master role."""
    membership = current_user.memberships[0] if current_user.memberships else None
    if membership and membership.role and membership.role.name == "master":
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Master admin access required",
    )


def require_master_no_impersonation(
    current_user: User = Depends(get_current_user_no_impersonation)
) -> User:
    """Require master role, rejecting impersonation tokens."""
    membership = current_user.memberships[0] if current_user.memberships else None
    if membership and membership.role and membership.role.name == "master":
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Master admin access required",
    )


async def require_primary_admin(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to require primary admin (only primary admin can manage billing)."""
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the primary administrator can manage billing"
        )
    
    return current_user


async def require_primary_admin_no_impersonation(
    current_user: User = Depends(require_admin_no_impersonation),
    db: Session = Depends(get_db)
) -> User:
    """Require primary admin, rejecting impersonation tokens."""
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the primary administrator can manage billing"
        )
    
    return current_user


async def require_active_subscription(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    """
    Require the admin's organization to have an active subscription.
    Active = active, trialing, or past_due (grace period while Stripe retries).
    Returns 402 Payment Required for all other statuses so the frontend
    can redirect to /admin/billing automatically.
    """
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
    ).first()

    if not membership or not membership.organization_id:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required to access the admin dashboard",
        )

    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    if org and org.is_comped:
        return current_user

    sub = db.query(Subscription).filter(
        Subscription.organization_id == membership.organization_id
    ).order_by(desc(Subscription.created_at)).first()

    if not sub or sub.status not in _ACTIVE_SUBSCRIPTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required to access the admin dashboard",
        )

    return current_user


async def require_view_subscription(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    """
    Allow admin GET (read-only) endpoints for canceled/unpaid subscriptions.
    Only blocks when no subscription record exists at all (admin never subscribed).
    Returns 402 with detail='no_subscription' so the frontend redirects to billing.
    """
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
    ).first()

    if not membership or not membership.organization_id:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="no_subscription",
        )

    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    if org and org.is_comped:
        return current_user

    sub = db.query(Subscription).filter(
        Subscription.organization_id == membership.organization_id
    ).order_by(desc(Subscription.created_at)).first()

    if not sub or sub.status not in _VIEW_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="no_subscription",
        )

    return current_user


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """Dependency to optionally get current user (returns None if not authenticated)."""
    try:
        return get_current_user(request, credentials, db)
    except HTTPException:
        return None
