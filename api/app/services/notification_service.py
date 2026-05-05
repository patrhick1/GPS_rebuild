"""
Notification service for creating and querying in-app notifications.
"""
import logging
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.notification import Notification

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user_id: UUID,
    type: str,
    title: str,
    message: str,
    link: Optional[str] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[UUID] = None,
    commit: bool = True,
) -> Notification:
    """Create a new notification for a user.

    Pass ``commit=False`` when fanning out a batch — caller is then responsible
    for calling ``db.commit()`` exactly once after the loop.
    """
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(notification)
    if commit:
        db.commit()
        db.refresh(notification)
    return notification


def create_notifications_bulk(db: Session, rows: Iterable[dict]) -> int:
    """Insert many notifications in a single transaction. Returns the count.

    ``rows`` are dicts with the same keys as ``create_notification`` parameters
    (excluding ``commit``). Used for admin/master fan-outs where a single church
    event creates one notification per admin — historically each was a separate
    INSERT+COMMIT, which doesn't scale past a handful of admins.
    """
    notifications = [Notification(**row) for row in rows]
    if not notifications:
        return 0
    db.add_all(notifications)
    db.commit()
    return len(notifications)


def get_notifications(
    db: Session,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
) -> dict:
    """Get paginated notifications for a user with counts."""
    query = db.query(Notification).filter(Notification.user_id == user_id)

    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total_count = query.count()
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .scalar()
    )

    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "notifications": notifications,
        "total_count": total_count,
        "unread_count": unread_count,
    }


def get_unread_count(db: Session, user_id: UUID) -> int:
    """Get the number of unread notifications for a user."""
    return (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .scalar()
    )


def mark_read(db: Session, notification_id: UUID, user_id: UUID) -> bool:
    """Mark a single notification as read. Returns False if not found or not owned."""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notification:
        return False
    notification.is_read = True
    db.commit()
    return True


def mark_all_read(db: Session, user_id: UUID) -> int:
    """Mark all unread notifications as read. Returns count of affected rows."""
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return count
