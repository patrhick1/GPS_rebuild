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
from slowapi.util import get_remote_address

# Shared limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limit constants
PUBLIC_AUTH_RATE = "5/minute"
PASSWORD_RESET_RATE = "3/minute"
AUTHENTICATED_RATE = "100/minute"
ADMIN_RATE = "50/minute"
MASTER_RATE = "30/minute"
EXPORT_RATE = "5/hour"
