from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.role import Role
from app.models.membership import Membership

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    Checks both Authorization header and cookie.
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
    
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
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
    
    return user


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


def require_master(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require master role."""
    membership = current_user.memberships[0] if current_user.memberships else None
    if membership and membership.role and membership.role.name == "master":
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Master admin access required",
    )


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
