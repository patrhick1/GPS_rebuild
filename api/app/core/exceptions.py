"""
Custom exceptions with secure error messages.

These exceptions hide sensitive details in production while providing
full debugging information in development mode.
"""
from fastapi import HTTPException
from app.core.config import settings


class SecureHTTPException(HTTPException):
    """
    HTTPException that hides sensitive details in production.
    
    In DEBUG mode, full error details are shown.
    In production, generic error messages are returned.
    """
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        debug_detail: str = None,
        headers: dict = None
    ):
        # In debug mode, show the detailed error
        if settings.DEBUG and debug_detail:
            message = f"{detail} - Debug: {debug_detail}"
        else:
            message = detail
        
        super().__init__(status_code=status_code, detail=message, headers=headers)


def handle_exception(e: Exception, operation: str = "processing your request") -> SecureHTTPException:
    """
    Convert any exception to a secure HTTP exception.
    
    Usage:
        try:
            risky_operation()
        except Exception as e:
            raise handle_exception(e, "creating subscription")
    
    Args:
        e: The exception that was raised
        operation: Description of what was being attempted
        
    Returns:
        SecureHTTPException with generic message (or detailed in DEBUG mode)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Always log the full error with traceback
    logger.error(f"Error {operation}: {e}", exc_info=True)
    
    # Return generic message in production, detailed in debug
    return SecureHTTPException(
        status_code=400,
        detail=f"An error occurred {operation}. Please try again.",
        debug_detail=str(e)
    )


def handle_stripe_exception(e: Exception) -> SecureHTTPException:
    """
    Handle Stripe-specific exceptions securely.
    
    Args:
        e: The Stripe exception that was raised
        
    Returns:
        SecureHTTPException with payment-specific message
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the full error
    logger.error(f"Stripe error: {e}", exc_info=True)
    
    # Check if it's a Stripe error with a user-friendly message
    error_message = "An error occurred processing your payment. Please try again."
    
    if hasattr(e, 'user_message') and e.user_message:
        # Use Stripe's user-friendly message if available
        error_message = e.user_message
    
    return SecureHTTPException(
        status_code=400,
        detail=error_message,
        debug_detail=str(e)
    )
