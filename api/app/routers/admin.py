"""
Church Admin API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import csv
import io
import secrets
import string

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user, require_admin
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.role import Role
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.invitation import Invitation
from app.schemas.admin import (
    MemberListResponse,
    MemberDetail,
    MemberUpdate,
    InviteCreate,
    InviteResponse,
    InviteListResponse,
    PendingMember,
    ChurchSettings,
    ChurchStats,
    BulkInviteRequest,
    BulkInviteResponse,
)

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
async def get_members(
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get members of the admin's organization"""
    
    org = get_admin_organization(db, current_user)
    
    # Base query
    query = db.query(User, Membership).join(Membership).filter(
        Membership.organization_id == org.id
    )
    
    # Apply filters
    if search:
        query = query.filter(
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    
    if status:
        query = query.filter(Membership.status == status)
    
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
        
        # Get latest assessment
        latest = db.query(Assessment).filter(
            Assessment.user_id == user.id,
            Assessment.status == "completed"
        ).order_by(Assessment.completed_at.desc()).first()
        
        member_list.append(MemberDetail(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            status=membership.status,
            role=membership.role.name if membership.role else None,
            joined_at=membership.created_at,
            assessment_count=assessment_count,
            last_assessment_date=latest.completed_at if latest else None,
            phone_number=user.phone_number
        ))
    
    return MemberListResponse(
        members=member_list,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/members/{member_id}", response_model=MemberDetail)
async def get_member_detail(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
    
    # Get latest assessment
    latest = db.query(Assessment).filter(
        Assessment.user_id == user.id,
        Assessment.status == "completed"
    ).order_by(Assessment.completed_at.desc()).first()
    
    return MemberDetail(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        status=membership.status,
        role=membership.role.name if membership.role else None,
        joined_at=membership.created_at,
        assessment_count=assessment_count,
        last_assessment_date=latest.completed_at if latest else None,
        phone_number=user.phone_number
    )


@router.put("/members/{member_id}")
async def update_member(
    member_id: str,
    update: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
    
    # Update role if provided
    if update.role:
        role = db.query(Role).filter(Role.name == update.role).first()
        if role:
            membership.role_id = role.id
    
    # Update status if provided
    if update.status:
        membership.status = update.status
    
    db.commit()
    
    return {"message": "Member updated successfully"}


@router.delete("/members/{member_id}")
async def remove_member(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
    
    # Set organization to null (make independent)
    membership.organization_id = None
    membership.status = "active"
    db.commit()
    
    return {"message": "Member removed from organization"}


@router.get("/invites", response_model=InviteListResponse)
async def get_invites(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
async def create_invite(
    invite: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)
    
    # TODO: Send email via Resend
    
    return InviteResponse(
        id=new_invite.id,
        email=new_invite.email,
        status=new_invite.status,
        created_at=new_invite.created_at,
        expires_at=new_invite.expires_at,
        accepted_at=new_invite.accepted_at
    )


@router.post("/invites/bulk", response_model=BulkInviteResponse)
async def bulk_invite(
    request: BulkInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create multiple invitations"""
    
    org = get_admin_organization(db, current_user)
    
    created = []
    failed = []
    
    for email in request.emails:
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
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            
            db.add(new_invite)
            created.append(email)
            
        except Exception as e:
            failed.append({"email": email, "reason": str(e)})
    
    db.commit()
    
    return BulkInviteResponse(
        created_count=len(created),
        created_emails=created,
        failed=failed
    )


@router.post("/invites/csv")
async def invite_from_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
                expires_at=datetime.utcnow() + timedelta(days=7)
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
async def resend_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
    invite.expires_at = datetime.utcnow() + timedelta(days=7)
    db.commit()
    
    # TODO: Resend email
    
    return {"message": "Invitation resent"}


@router.delete("/invites/{invite_id}")
async def cancel_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
async def get_pending_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
async def approve_pending(
    membership_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
async def decline_pending(
    membership_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
async def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
async def update_settings(
    settings: ChurchSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
async def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
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
    
    # Assessment count
    assessment_count = db.query(Assessment).join(Membership).filter(
        Membership.organization_id == org.id,
        Assessment.status == "completed"
    ).count()
    
    return ChurchStats(
        total_members=member_count,
        active_members=active_count,
        pending_members=pending_count,
        total_assessments=assessment_count
    )
