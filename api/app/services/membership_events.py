"""Side effects to fire when a user becomes affiliated with a church.

Three callsites trigger this:
  1. self-registration with organization_key  (auth_service.register_user)
  2. admin-approved pending request           (admin.approve_pending)
  3. invite acceptance                        (auth.complete_invitation flow)

Each call:
  - creates a `member_joined` notification for every admin of the church
  - fires a `user_registered` webhook (Zapier-shaped)

Both side effects are wrapped in try/except by the caller — never fail the
parent request because of a notification or webhook hiccup.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.services import notification_service
from app.services.webhook_payloads import build_user_registered_payload
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


def _admins_of_org(db: Session, organization_id) -> list[Membership]:
    return (
        db.query(Membership)
        .filter(
            Membership.organization_id == organization_id,
            Membership.status == "active",
            Membership.role.has(name="admin"),
        )
        .options(joinedload(Membership.user))
        .all()
    )


def fire_member_joined_events(
    db: Session,
    *,
    user: User,
    organization: Organization,
    registered_at: Optional[datetime] = None,
) -> None:
    """Run after a Membership row has been committed for `user` in `organization`.
    Caller is expected to have committed the membership before calling this so
    that any DB query inside (e.g. admin lookup) sees consistent state."""
    registered_at = registered_at or datetime.now(timezone.utc)
    member_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email

    # 1. Notify every admin of this church.
    try:
        for admin_m in _admins_of_org(db, organization.id):
            try:
                notification_service.create_notification(
                    db,
                    user_id=admin_m.user.id,
                    type="member_joined",
                    title=f"{member_name} joined {organization.name}",
                    message=f"{member_name} is now a member of your church.",
                    link=f"/admin?member={user.id}",
                    reference_type="user",
                    reference_id=user.id,
                )
            except Exception:
                logger.exception("Failed to create member_joined notification for admin %s", admin_m.user_id)
    except Exception:
        logger.exception("Failed during member_joined admin notification fan-out")

    # 2. Fire user_registered webhook (no-op if no config).
    try:
        payload = build_user_registered_payload(
            user=user,
            organization=organization,
            registered_at=registered_at,
        )
        WebhookService(db).fire(organization.id, "user_registered", payload)
    except Exception:
        logger.exception("Failed to fire user_registered webhook")


def fire_member_requested_event(
    db: Session,
    *,
    user: User,
    organization: Organization,
) -> None:
    """Run after a pending Membership row is committed (status='pending').
    Notifies admins so they can approve/decline. No webhook fires here — only
    `user_registered` does, and that only after approval."""
    member_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
    try:
        for admin_m in _admins_of_org(db, organization.id):
            try:
                notification_service.create_notification(
                    db,
                    user_id=admin_m.user.id,
                    type="member_requested",
                    title=f"{member_name} requested to join {organization.name}",
                    message=f"{member_name} is awaiting your approval to join your church.",
                    link="/admin?tab=pending",
                    reference_type="user",
                    reference_id=user.id,
                )
            except Exception:
                logger.exception("Failed to create member_requested notification for admin %s", admin_m.user_id)
    except Exception:
        logger.exception("Failed during member_requested admin notification fan-out")


def fire_church_created_event(
    db: Session,
    *,
    organization: Organization,
    actor_user_id=None,
) -> None:
    """Notify all master admins (excluding the actor if provided) that a new
    church was created. No webhook fires for this event."""
    from app.models.role import Role  # local import to avoid circulars

    try:
        masters = (
            db.query(User)
            .join(Membership, Membership.user_id == User.id)
            .join(Role, Role.id == Membership.role_id)
            .filter(Role.name == "master")
        )
        if actor_user_id is not None:
            masters = masters.filter(User.id != actor_user_id)
        masters_list = masters.distinct().all()

        for master in masters_list:
            try:
                notification_service.create_notification(
                    db,
                    user_id=master.id,
                    type="church_created",
                    title=f"{organization.name} was created",
                    message=f"A new church '{organization.name}' has been added to the platform.",
                    link=f"/master?church={organization.id}",
                    reference_type="organization",
                    reference_id=organization.id,
                )
            except Exception:
                logger.exception("Failed to create church_created notification for master %s", master.id)
    except Exception:
        logger.exception("Failed during church_created notification fan-out")
