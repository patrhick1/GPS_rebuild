"""
Notification API endpoints for in-app notification center.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_verified_user
from app.models.user import User
from app.schemas.notification import NotificationListResponse, UnreadCountResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Get paginated notifications for the current user."""
    result = notification_service.get_notifications(
        db, current_user.id, limit=limit, offset=offset, unread_only=unread_only
    )
    return result


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Get the number of unread notifications (lightweight endpoint for polling)."""
    count = notification_service.get_unread_count(db, current_user.id)
    return {"count": count}


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    success = notification_service.mark_read(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"message": "Notification marked as read"}


@router.patch("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    count = notification_service.mark_all_read(db, current_user.id)
    return {"message": f"Marked {count} notifications as read"}
