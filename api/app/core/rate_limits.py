"""
Centralized rate limiting configuration for the GPS API.

Tiered rate limits by endpoint sensitivity:
- Public auth: 5/minute (login, register)
- Password reset: 3/minute
- Authenticated standard: 100/minute
- Admin operations: 50/minute
- Master operations: 30/minute
- Data export: 5/hour (sensitive data export)
"""

from slowapi import Limiter

from app.core.network import get_client_ip


def _key_func(request) -> str:
    """Bucket rate limits per real client IP, not per Render proxy.

    Falls back to a stable string if the request has no usable client
    info (limiter still works, just one global bucket as a safety net).
    """
    return get_client_ip(request) or "unknown"


# Shared limiter instance
limiter = Limiter(key_func=_key_func)

# Rate limit constants
PUBLIC_AUTH_RATE = "5/minute"
PASSWORD_RESET_RATE = "3/minute"
AUTHENTICATED_RATE = "100/minute"
ADMIN_RATE = "50/minute"
MASTER_RATE = "30/minute"
EXPORT_RATE = "5/hour"
