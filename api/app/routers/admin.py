"""
Church Admin API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc
from datetime import datetime, timedelta, timezone
import csv
import io
import secrets
import string

from app.core.database import get_db
from app.core.rate_limits import limiter, ADMIN_RATE
from app.core.audit import audit_action
from app.dependencies.auth import get_current_active_user, require_admin, require_active_subscription, require_view_subscription, require_primary_admin
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.role import Role
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.gifts_passion import GiftsPassion
from app.models.myimpact_result import MyImpactResult
from app.models.invitation import Invitation
from app.schemas.admin import (
    MemberListResponse,
    MemberDetail,
    MemberUpdate,
    TransferPrimaryAdminRequest,
    InviteCreate,
    InviteResponse,
    InviteListResponse,
    PendingMember,
    ChurchSettings,
    ChurchStats,
    BulkInviteRequest,
    BulkInviteResponse,
)
from app.schemas.assessment import GradedAssessmentResponse, GradedMyImpactResponse
from app.services.scoring_service import ScoringService
from app.services.myimpact_scoring_service import MyImpactScoringService
from app.services.email_service import send_invite_email

router = APIRouter(prefix="/admin", tags=["Church Admin"])


def get_admin_organization(db: Session, user: User) -> Organization:
    """Get the organization that the user is an admin of"""
    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.role.has(name="admin")
    ).first()
    
    if not membership or not membership.organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an admin of any organization"
        )
    
    return membership.organization


@router.get("/members", response_model=MemberListResponse)
@limiter.limit(ADMIN_RATE)
async def get_members(
    request: Request,
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view_subscription)
):
    """Get members of the admin's organization"""
    
    org = get_admin_organization(db, current_user)
    
    # Base query
    query = db.query(User, Membership).join(Membership).filter(
        Membership.organization_id == org.id
    )
    
    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        full_name = func.concat(User.first_name, ' ', User.last_name)
        query = query.filter(
            (User.first_name.ilike(search_pattern)) |
            (User.last_name.ilike(search_pattern)) |
            (User.email.ilike(search_pattern)) |
            (full_name.ilike(search_pattern))
        )
    
    if status:
        query = query.filter(Membership.status == status)
    
    # Order: admins/masters first, then by latest assessment date descending
    is_admin_rank = case(
        (Role.name.in_(['admin', 'master']), 0),
        else_=1
    )
    latest_assessment_date = (
        db.query(func.max(Assessment.completed_at))
        .filter(Assessment.user_id == User.id, Assessment.status == "completed")
        .correlate(User)
        .scalar_subquery()
    )
    query = query.join(Role, Membership.role_id == Role.id).order_by(
        is_admin_rank,
        desc(latest_assessment_date)
    )

    # Get total count
    total = query.count()

    # Paginate
    members = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Build response
    member_list = []
    for user, membership in members:
        # Get assessment count
        assessment_count = db.query(Assessment).filter(
            Assessment.user_id == user.id,
            Assessment.status == "completed"
        ).count()

        # Get latest GPS assessment
        latest_gps = db.query(Assessment).filter(
            Assessment.user_id == user.id,
            Assessment.status == "completed",
            Assessment.instrument_type == "gps"
        ).order_by(Assessment.completed_at.desc()).first()

        # Get latest MyImpact assessment
        latest_myimpact = db.query(Assessment).filter(
            Assessment.user_id == user.id,
            Assessment.status == "completed",
            Assessment.instrument_type == "myimpact"
        ).order_by(Assessment.completed_at.desc()).first()

        # Use the most recent of either for last_assessment_date
        latest_date = None
        if latest_gps and latest_myimpact:
            latest_date = max(latest_gps.completed_at, latest_myimpact.completed_at)
        elif latest_gps:
            latest_date = latest_gps.completed_at
        elif latest_myimpact:
            latest_date = latest_myimpact.completed_at

        # Get top gifts and passions from latest GPS assessment result
        top_gifts = []
        top_passions = []
        if latest_gps:
            result = db.query(AssessmentResult).filter(
                AssessmentResult.assessment_id == latest_gps.id
            ).first()
            if result:
                top_gifts = _get_member_gifts(db, result)
                top_passions = _get_member_passions(db, result)

        # Get MyImpact scores from latest MyImpact result
        myimpact_character_score = None
        myimpact_calling_score = None
        myimpact_score_val = None
        if latest_myimpact:
            mi_result = db.query(MyImpactResult).filter(
                MyImpactResult.assessment_id == latest_myimpact.id
            ).first()
            if mi_result:
                myimpact_character_score = mi_result.character_score
                myimpact_calling_score = mi_result.calling_score
                myimpact_score_val = mi_result.myimpact_score

        role_name = membership.role.name if membership.role else None

        member_list.append(MemberDetail(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            status=membership.status,
            role=role_name,
            is_admin=role_name == "admin",
            is_primary_admin=membership.is_primary_admin or False,
            joined_at=membership.created_at,
            assessment_count=assessment_count,
            last_assessment_date=latest_date,
            latest_gps_assessment_id=latest_gps.id if latest_gps else None,
            latest_myimpact_assessment_id=latest_myimpact.id if latest_myimpact else None,
            phone_number=user.phone_number,
            top_gifts=top_gifts,
            top_passions=top_passions,
            myimpact_character_score=myimpact_character_score,
            myimpact_calling_score=myimpact_calling_score,
            myimpact_score=myimpact_score_val,
        ))
    
    def _sort_key(m):
        d = m.last_assessment_date
        if d is None:
            return datetime.min
        if d.tzinfo is not None:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d

    member_list.sort(key=_sort_key, reverse=True)

    return MemberListResponse(
        members=member_list,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/members/{member_id}", response_model=MemberDetail)
@limiter.limit(ADMIN_RATE)
async def get_member_detail(
    request: Request,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view_subscription)
):
    """Get detailed info about a specific member"""
    
    org = get_admin_organization(db, current_user)
    
    # Verify member belongs to organization
    membership = db.query(Membership).filter(
        Membership.user_id == member_id,
        Membership.organization_id == org.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    user = membership.user
    
    # Get assessment count
    assessment_count = db.query(Assessment).filter(
        Assessment.user_id == user.id,
        Assessment.status == "completed"
    ).count()
    
    # Get latest GPS and MyImpact assessments separately
    latest_gps = db.query(Assessment).filter(
        Assessment.user_id == user.id,
        Assessment.status == "completed",
        Assessment.instrument_type == "gps"
    ).order_by(Assessment.completed_at.desc()).first()

    latest_myimpact = db.query(Assessment).filter(
        Assessment.user_id == user.id,
        Assessment.status == "completed",
        Assessment.instrument_type == "myimpact"
    ).order_by(Assessment.completed_at.desc()).first()

    latest_date = None
    if latest_gps and latest_myimpact:
        latest_date = max(latest_gps.completed_at, latest_myimpact.completed_at)
    elif latest_gps:
        latest_date = latest_gps.completed_at
    elif latest_myimpact:
        latest_date = latest_myimpact.completed_at

    return MemberDetail(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        status=membership.status,
        role=membership.role.name if membership.role else None,
        joined_at=membership.created_at,
        assessment_count=assessment_count,
        last_assessment_date=latest_date,
        latest_gps_assessment_id=latest_gps.id if latest_gps else None,
        latest_myimpact_assessment_id=latest_myimpact.id if latest_myimpact else None,
        phone_number=user.phone_number
    )


@router.get("/members/{member_id}/results")
@limiter.limit(ADMIN_RATE)
async def get_member_results(
    request: Request,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view_subscription)
):
    """Get full graded assessment results for a member"""
    import uuid as uuid_mod

    org = get_admin_organization(db, current_user)

    # Verify member belongs to admin's organization
    membership = db.query(Membership).filter(
        Membership.user_id == member_id,
        Membership.organization_id == org.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Get latest completed assessment
    assessment = db.query(Assessment).filter(
        Assessment.user_id == member_id,
        Assessment.status == "completed"
    ).order_by(Assessment.completed_at.desc()).first()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed assessment found for this member"
        )

    # Route to correct scoring service
    if assessment.instrument_type == "myimpact":
        scoring_service = MyImpactScoringService(db)
        graded = scoring_service.grade_assessment(assessment)
        return GradedMyImpactResponse(
            character=graded.to_dict()["character"],
            calling=graded.to_dict()["calling"],
            myimpact_score=graded.myimpact_score
        )
    else:
        scoring_service = ScoringService(db)
        graded = scoring_service.grade_assessment(assessment)
        return GradedAssessmentResponse(
            gifts=[
                {"id": g.id, "name": g.name, "short_code": g.short_code, "description": g.description, "points": g.points}
                for g in graded.gifts
            ],
            top_gifts=[
                {"id": g.id, "name": g.name, "short_code": g.short_code, "description": g.description, "points": g.points}
                for g in graded.top_gifts
            ],
            passions=[
                {"id": p.id, "name": p.name, "short_code": p.short_code, "description": p.description, "points": p.points}
                for p in graded.passions
            ],
            top_passions=[
                {"id": p.id, "name": p.name, "short_code": p.short_code, "description": p.description, "points": p.points}
                for p in graded.top_passions
            ],
            abilities=graded.abilities,
            people=graded.people,
            causes=graded.causes,
            stories=[
                {"question": s.question, "answer": s.answer, "question_es": s.question_es}
                for s in graded.stories
            ]
        )


@router.put("/members/{member_id}")
@limiter.limit(ADMIN_RATE)
@audit_action("member_updated", "user")
async def update_member(
    request: Request,
    member_id: str,
    update: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Update member role or status"""
    
    org = get_admin_organization(db, current_user)
    
    membership = db.query(Membership).filter(
        Membership.user_id == member_id,
        Membership.organization_id == org.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Prevent demoting the primary admin
    if membership.is_primary_admin and update.role and update.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot demote the primary administrator. Transfer primary status first."
        )
    
    # Update role if provided
    if update.role:
        role = db.query(Role).filter(Role.name == update.role).first()
        if role:
            membership.role_id = role.id
            # When promoting to admin, always set as secondary (is_primary_admin=False)
            if update.role == "admin":
                membership.is_primary_admin = False
    
    # Update status if provided
    if update.status:
        membership.status = update.status
    
    db.commit()
    
    return {"message": "Member updated successfully"}


@router.delete("/members/{member_id}")
@limiter.limit(ADMIN_RATE)
@audit_action("member_removed", "user")
async def remove_member(
    request: Request,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Remove member from organization"""
    
    org = get_admin_organization(db, current_user)
    
    membership = db.query(Membership).filter(
        Membership.user_id == member_id,
        Membership.organization_id == org.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Prevent removing the primary admin
    if membership.is_primary_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove the primary administrator. Transfer primary status first."
        )
    
    # Set organization to null (make independent)
    membership.organization_id = None
    membership.status = "active"
    db.commit()
    
    return {"message": "Member removed from organization"}


@router.post("/transfer-primary-admin")
@limiter.limit(ADMIN_RATE)
async def transfer_primary_admin(
    request: Request,
    body: TransferPrimaryAdminRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_primary_admin)
):
    """Transfer primary admin status to another admin in the organization.
    The current primary admin becomes a secondary admin."""

    org = get_admin_organization(db, current_user)

    # Verify target is a different active admin (not primary) in the same org
    target_membership = db.query(Membership).filter(
        Membership.user_id == body.target_member_id,
        Membership.organization_id == org.id,
        Membership.is_primary_admin == False,
        Membership.status == "active",
    ).first()

    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target member not found or is not an active secondary administrator in this organization"
        )

    if target_membership.role and target_membership.role.name not in ("admin", "master"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primary admin status can only be transferred to an existing administrator"
        )

    # Get current primary admin's membership
    current_membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_primary_admin == True
    ).first()

    if not current_membership:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Current primary admin membership not found"
        )

    # Atomic swap — both happen or neither does
    current_membership.is_primary_admin = False
    target_membership.is_primary_admin = True
    db.commit()

    # Audit log
    from app.core.audit import log_audit_event
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="primary_admin_transferred",
        target_type="user",
        target_id=str(target_membership.user_id),
        details={
            "previous_primary_id": str(current_user.id),
            "new_primary_id": str(target_membership.user_id),
            "organization_id": str(org.id),
        }
    )

    return {"message": "Primary admin status transferred successfully"}


@router.get("/invites", response_model=InviteListResponse)
@limiter.limit(ADMIN_RATE)
async def get_invites(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view_subscription)
):
    """Get list of invitations"""
    
    org = get_admin_organization(db, current_user)
    
    query = db.query(Invitation).filter(Invitation.organization_id == org.id)
    
    if status:
        query = query.filter(Invitation.status == status)
    
    invites = query.order_by(Invitation.created_at.desc()).all()
    
    return InviteListResponse(
        invites=[
            InviteResponse(
                id=inv.id,
                email=inv.email,
                status=inv.status,
                created_at=inv.created_at,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at
            )
            for inv in invites
        ]
    )


@router.post("/invites", response_model=InviteResponse)
@limiter.limit(ADMIN_RATE)
@audit_action("invite_created", "invitation")
async def create_invite(
    request: Request,
    invite: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Create a new invitation"""
    
    org = get_admin_organization(db, current_user)
    
    # Generate unique token
    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    new_invite = Invitation(
        sign_up_key=token,
        email=invite.email,
        organization_id=org.id,
        created_by=current_user.id,
        status="sent",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)

    send_invite_email(
        to_email=new_invite.email,
        org_name=org.name,
        org_key=org.key,
        invite_token=new_invite.sign_up_key,
    )

    return InviteResponse(
        id=new_invite.id,
        email=new_invite.email,
        status=new_invite.status,
        created_at=new_invite.created_at,
        expires_at=new_invite.expires_at,
        accepted_at=new_invite.accepted_at
    )


@router.post("/invites/bulk", response_model=BulkInviteResponse)
@limiter.limit(ADMIN_RATE)
@audit_action("bulk_invites_created", "invitation")
async def bulk_invite(
    request: Request,
    invite_request: BulkInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Create multiple invitations"""
    
    org = get_admin_organization(db, current_user)
    
    created = []
    failed = []
    pending_emails: list[tuple[str, str]] = []  # (email, token)

    for email in invite_request.emails:
        try:
            # Check if already invited
            existing = db.query(Invitation).filter(
                Invitation.email == email,
                Invitation.organization_id == org.id,
                Invitation.status == "sent"
            ).first()

            if existing:
                failed.append({"email": email, "reason": "Already invited"})
                continue

            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

            new_invite = Invitation(
                sign_up_key=token,
                email=email,
                organization_id=org.id,
                created_by=current_user.id,
                status="sent",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )

            db.add(new_invite)
            created.append(email)
            pending_emails.append((email, token))

        except Exception as e:
            failed.append({"email": email, "reason": str(e)})

    db.commit()

    for email, token in pending_emails:
        send_invite_email(
            to_email=email,
            org_name=org.name,
            org_key=org.key,
            invite_token=token,
        )

    return BulkInviteResponse(
        created_count=len(created),
        created_emails=created,
        failed=failed
    )


@router.post("/invites/csv")
@limiter.limit(ADMIN_RATE)
async def invite_from_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Upload CSV file with emails to invite"""
    
    org = get_admin_organization(db, current_user)
    
    # Read CSV
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.reader(io.StringIO(decoded))
    
    emails = []
    for row in reader:
        if row and row[0]:
            email = row[0].strip()
            if email:
                emails.append(email)
    
    # Create invites
    created = []
    failed = []
    
    for email in emails:
        try:
            existing = db.query(Invitation).filter(
                Invitation.email == email,
                Invitation.organization_id == org.id,
                Invitation.status == "sent"
            ).first()
            
            if existing:
                failed.append({"email": email, "reason": "Already invited"})
                continue
            
            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            
            new_invite = Invitation(
                sign_up_key=token,
                email=email,
                organization_id=org.id,
                created_by=current_user.id,
                status="sent",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            
            db.add(new_invite)
            created.append(email)
            
        except Exception as e:
            failed.append({"email": email, "reason": str(e)})
    
    db.commit()
    
    return {
        "created_count": len(created),
        "created_emails": created,
        "failed": failed
    }


@router.post("/invites/{invite_id}/resend")
@limiter.limit(ADMIN_RATE)
async def resend_invite(
    request: Request,
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Resend an invitation"""
    
    org = get_admin_organization(db, current_user)
    
    invite = db.query(Invitation).filter(
        Invitation.id == invite_id,
        Invitation.organization_id == org.id
    ).first()
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Extend expiry
    invite.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    db.commit()

    send_invite_email(
        to_email=invite.email,
        org_name=org.name,
        org_key=org.key,
        invite_token=invite.sign_up_key,
    )

    return {"message": "Invitation resent"}


@router.delete("/invites/{invite_id}")
@limiter.limit(ADMIN_RATE)
async def cancel_invite(
    request: Request,
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Cancel an invitation"""
    
    org = get_admin_organization(db, current_user)
    
    invite = db.query(Invitation).filter(
        Invitation.id == invite_id,
        Invitation.organization_id == org.id
    ).first()
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    invite.status = "revoked"
    db.commit()
    
    return {"message": "Invitation cancelled"}


@router.get("/pending", response_model=List[PendingMember])
@limiter.limit(ADMIN_RATE)
async def get_pending_members(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view_subscription)
):
    """Get pending membership requests"""
    
    org = get_admin_organization(db, current_user)
    
    pending = db.query(User, Membership).join(Membership).filter(
        Membership.organization_id == org.id,
        Membership.status == "pending"
    ).all()
    
    return [
        PendingMember(
            membership_id=membership.id,
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            requested_at=membership.created_at
        )
        for user, membership in pending
    ]


@router.post("/pending/{membership_id}/approve")
@limiter.limit(ADMIN_RATE)
@audit_action("membership_approved", "membership")
async def approve_pending(
    request: Request,
    membership_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Approve a pending membership request"""
    
    org = get_admin_organization(db, current_user)
    
    membership = db.query(Membership).filter(
        Membership.id == membership_id,
        Membership.organization_id == org.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership request not found"
        )
    
    membership.status = "active"
    db.commit()
    
    return {"message": "Member approved"}


@router.post("/pending/{membership_id}/decline")
@limiter.limit(ADMIN_RATE)
@audit_action("membership_declined", "membership")
async def decline_pending(
    request: Request,
    membership_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Decline a pending membership request"""
    
    org = get_admin_organization(db, current_user)
    
    membership = db.query(Membership).filter(
        Membership.id == membership_id,
        Membership.organization_id == org.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership request not found"
        )
    
    membership.status = "declined"
    db.commit()
    
    return {"message": "Member request declined"}


@router.get("/settings", response_model=ChurchSettings)
@limiter.limit(ADMIN_RATE)
async def get_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view_subscription)
):
    """Get church settings"""
    
    org = get_admin_organization(db, current_user)
    
    return ChurchSettings(
        id=org.id,
        name=org.name,
        key=org.key,
        city=org.city,
        state=org.state,
        country=org.country,
        preferred_instrument=org.preferred_instrument
    )


@router.put("/settings")
@limiter.limit(ADMIN_RATE)
async def update_settings(
    request: Request,
    settings: ChurchSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Update church settings"""
    
    org = get_admin_organization(db, current_user)
    
    if settings.name:
        org.name = settings.name
    if settings.city:
        org.city = settings.city
    if settings.state:
        org.state = settings.state
    if settings.country:
        org.country = settings.country
    if settings.preferred_instrument:
        org.preferred_instrument = settings.preferred_instrument
    
    db.commit()
    
    return {"message": "Settings updated"}


@router.get("/stats", response_model=ChurchStats)
@limiter.limit(ADMIN_RATE)
async def get_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view_subscription)
):
    """Get church statistics"""
    
    org = get_admin_organization(db, current_user)
    
    # Member count
    member_count = db.query(Membership).filter(
        Membership.organization_id == org.id
    ).count()
    
    # Active members
    active_count = db.query(Membership).filter(
        Membership.organization_id == org.id,
        Membership.status == "active"
    ).count()
    
    # Pending members
    pending_count = db.query(Membership).filter(
        Membership.organization_id == org.id,
        Membership.status == "pending"
    ).count()
    
    # Assessment counts by type
    gps_count = db.query(Assessment).join(
        Membership, Assessment.user_id == Membership.user_id
    ).filter(
        Membership.organization_id == org.id,
        Assessment.status == "completed",
        Assessment.instrument_type == "gps"
    ).count()

    myimpact_count = db.query(Assessment).join(
        Membership, Assessment.user_id == Membership.user_id
    ).filter(
        Membership.organization_id == org.id,
        Assessment.status == "completed",
        Assessment.instrument_type == "myimpact"
    ).count()

    assessment_count = gps_count + myimpact_count

    # Average MyImpact scores
    avg_scores = db.query(
        func.avg(MyImpactResult.character_score),
        func.avg(MyImpactResult.calling_score),
        func.avg(MyImpactResult.myimpact_score)
    ).join(
        Assessment, MyImpactResult.assessment_id == Assessment.id
    ).join(
        Membership, Assessment.user_id == Membership.user_id
    ).filter(
        Membership.organization_id == org.id,
        Assessment.status == "completed"
    ).first()

    avg_character = round(float(avg_scores[0]), 1) if avg_scores[0] else None
    avg_calling = round(float(avg_scores[1]), 1) if avg_scores[1] else None
    avg_myimpact = round(float(avg_scores[2]), 1) if avg_scores[2] else None

    return ChurchStats(
        total_members=member_count,
        active_members=active_count,
        pending_members=pending_count,
        total_assessments=assessment_count,
        gps_assessments=gps_count,
        myimpact_assessments=myimpact_count,
        avg_character_score=avg_character,
        avg_calling_score=avg_calling,
        avg_myimpact_score=avg_myimpact,
    )


# ── Helpers for member gift/passion summaries ──

def _get_member_gifts(db: Session, result: AssessmentResult):
    """Get top gift short_codes for the admin members table."""
    gifts = []
    for gift_id, score in [
        (result.gift_1_id, result.spiritual_gift_1_score),
        (result.gift_2_id, result.spiritual_gift_2_score),
    ]:
        if gift_id:
            gift = db.query(GiftsPassion).filter(GiftsPassion.id == gift_id).first()
            if gift:
                gifts.append({"name": gift.name, "short_code": gift.short_code, "score": score or 0})
    return gifts


def _get_member_passions(db: Session, result: AssessmentResult):
    """Get top passion names for the admin members table."""
    passions = []
    for passion_id, score in [
        (result.passion_1_id, result.passion_1_score),
    ]:
        if passion_id:
            passion = db.query(GiftsPassion).filter(GiftsPassion.id == passion_id).first()
            if passion:
                passions.append({"name": passion.name, "short_code": passion.short_code, "score": score or 0})
    return passions


@router.get("/export/csv")
@limiter.limit(ADMIN_RATE)
async def export_church_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),  # No subscription check — export works even when canceled
):
    """
    Export all church member and assessment data as a CSV file.
    Accessible regardless of subscription status so admins can retrieve
    their data before access is fully removed.
    """
    org = get_admin_organization(db, current_user)

    memberships = db.query(Membership).filter(
        Membership.organization_id == org.id,
        Membership.status != "removed",
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "First Name", "Last Name", "Email", "Member Status", "Joined Date",
        "Assessment Type", "Assessment Completed",
        "Gift 1", "Gift 1 Score", "Gift 2", "Gift 2 Score",
        "Gift 3", "Gift 3 Score", "Gift 4", "Gift 4 Score",
        "Passion 1", "Passion 1 Score", "Passion 2", "Passion 2 Score",
        "Passion 3", "Passion 3 Score",
        "MyImpact Score", "Character Score", "Calling Score",
        "People", "Cause", "Abilities",
    ])

    for m in memberships:
        user = m.user
        if not user:
            continue

        base = [
            user.first_name or "",
            user.last_name or "",
            user.email or "",
            m.status,
            m.created_at.strftime("%Y-%m-%d") if m.created_at else "",
        ]

        # Get the latest completed assessment
        assessment = db.query(Assessment).filter(
            Assessment.user_id == user.id,
            Assessment.status == "completed",
        ).order_by(Assessment.completed_at.desc()).first()

        if not assessment:
            writer.writerow(base + [""] * 21)
            continue

        completed = assessment.completed_at.strftime("%Y-%m-%d") if assessment.completed_at else ""

        if assessment.instrument_type == "myimpact":
            mi = assessment.myimpact_results
            writer.writerow(base + [
                "MyImpact", completed,
                "", "", "", "", "", "", "", "",  # GPS gift/passion columns blank
                "", "", "", "", "", "",
                mi.myimpact_score if mi else "",
                mi.character_score if mi else "",
                mi.calling_score if mi else "",
                "", "", "",
            ])
        else:
            r = assessment.results
            gifts = []
            passions = []
            if r:
                for gid, gscore in [
                    (r.gift_1_id, r.spiritual_gift_1_score),
                    (r.gift_2_id, r.spiritual_gift_2_score),
                    (r.gift_3_id, r.spiritual_gift_3_score),
                    (r.gift_4_id, r.spiritual_gift_4_score),
                ]:
                    if gid:
                        gp = db.query(GiftsPassion).filter(GiftsPassion.id == gid).first()
                        gifts.append((gp.name if gp else "", gscore or ""))
                    else:
                        gifts.append(("", ""))
                for pid, pscore in [
                    (r.passion_1_id, r.passion_1_score),
                    (r.passion_2_id, r.passion_2_score),
                    (r.passion_3_id, r.passion_3_score),
                ]:
                    if pid:
                        gp = db.query(GiftsPassion).filter(GiftsPassion.id == pid).first()
                        passions.append((gp.name if gp else "", pscore or ""))
                    else:
                        passions.append(("", ""))

            while len(gifts) < 4:
                gifts.append(("", ""))
            while len(passions) < 3:
                passions.append(("", ""))

            writer.writerow(base + [
                "GPS", completed,
                gifts[0][0], gifts[0][1], gifts[1][0], gifts[1][1],
                gifts[2][0], gifts[2][1], gifts[3][0], gifts[3][1],
                passions[0][0], passions[0][1], passions[1][0], passions[1][1],
                passions[2][0], passions[2][1],
                "", "", "",  # MyImpact columns blank
                r.people if r else "", r.cause if r else "", r.abilities if r else "",
            ])

    output.seek(0)
    filename = f"{org.name.replace(' ', '-').lower()}-church-data.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
