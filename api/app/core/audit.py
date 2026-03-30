"""
Centralized audit logging utilities.

This module provides decorators and functions for comprehensive
audit logging across the application.
"""
from functools import wraps
from typing import Optional, Any
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def audit_action(action: str, target_type: Optional[str] = None):
    """
    Decorator to automatically log actions to the audit log.
    
    This decorator extracts the request, current_user, and db from the
    function arguments and creates an audit log entry after the function
    executes successfully.
    
    Usage:
        @router.post("/members/{member_id}")
        @audit_action("member_updated", "user")
        async def update_member(request: Request, member_id: str, ...)
    
    Args:
        action: The action being performed (e.g., "member_updated")
        target_type: The type of entity being acted upon (e.g., "user")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            request: Request = kwargs.get('request')
            current_user = kwargs.get('current_user')
            db: Session = kwargs.get('db')
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Log the action if we have the required dependencies
            if db and current_user:
                try:
                    # Extract target ID from result or kwargs
                    target_id = None
                    if result and hasattr(result, 'id'):
                        target_id = str(result.id)
                    elif 'member_id' in kwargs:
                        target_id = str(kwargs['member_id'])
                    elif 'user_id' in kwargs:
                        target_id = str(kwargs['user_id'])
                    elif 'invite_id' in kwargs:
                        target_id = str(kwargs['invite_id'])
                    elif 'membership_id' in kwargs:
                        target_id = str(kwargs['membership_id'])
                    elif 'assessment_id' in kwargs:
                        target_id = str(kwargs['assessment_id'])
                    
                    # Get IP address from request
                    ip_address = None
                    if request and hasattr(request, 'client') and request.client:
                        ip_address = request.client.host
                    
                    audit = AuditLog(
                        user_id=current_user.id,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        details={"ip_address": ip_address}
                    )
                    db.add(audit)
                    db.commit()
                except Exception:
                    # Don't let audit logging fail the request
                    db.rollback()
            
            return result
        return wrapper
    return decorator


def log_audit_event(
    db: Session,
    user_id: Any,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    Manually log an audit event.
    
    Use this function when you need to log an event that doesn't fit
    the decorator pattern or when you need more control over the log entry.
    
    Usage:
        log_audit_event(
            db=db,
            user_id=current_user.id,
            action="password_changed",
            target_type="user",
            target_id=str(current_user.id)
        )
    
    Args:
        db: Database session
        user_id: ID of the user performing the action (or None for anonymous)
        action: The action being performed
        target_type: Type of entity being acted upon
        target_id: ID of the entity being acted upon
        details: Additional details to store (dict)
    """
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {}
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()
