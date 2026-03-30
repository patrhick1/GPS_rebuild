from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    # bcrypt has a 72-byte limit, ensure we handle this correctly
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    is_impersonation: bool = False
) -> str:
    """
    Create a new access token.
    
    Args:
        data: Token payload data (must include 'sub' for user_id)
        expires_delta: Optional custom expiration time
        is_impersonation: If True, creates an impersonation token with shorter expiry
                         and explicit impersonation flag
    """
    to_encode = data.copy()
    
    # Use shorter expiry for impersonation tokens
    if is_impersonation:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    elif expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "impersonation": is_impersonation
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "impersonation": False  # Refresh tokens cannot be impersonation tokens
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode a JWT token.
    
    Returns the token payload if valid, None otherwise.
    Does NOT validate impersonation restrictions - use verify_token_not_impersonation
    for endpoints that should reject impersonation tokens.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token_not_impersonation(token: str) -> tuple[bool, Optional[dict], Optional[str]]:
    """
    Verify that a token is NOT an impersonation token.
    
    Returns:
        Tuple of (is_valid, payload_or_none, error_message_or_none)
    """
    payload = decode_token(token)
    
    if payload is None:
        return False, None, "Invalid or expired token"
    
    if payload.get("type") != "access":
        return False, None, "Invalid token type"
    
    if payload.get("impersonation") is True:
        return False, None, "Impersonation tokens cannot access this endpoint"
    
    return True, payload, None


def get_token_fingerprint(token: str) -> str:
    """
    Get a hash fingerprint of a token for database storage.
    
    This allows tokens to be validated without storing the full token.
    """
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def get_token_hash(token: str) -> str:
    """Get hash of token for secure storage/comparison."""
    return get_token_fingerprint(token)
