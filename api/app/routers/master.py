"""
Master Admin API endpoints
Full system access for master administrators
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone
import csv
import io

from app.core.database import get_db
from app.core.rate_limits import limiter, MASTER_RATE, EXPORT_RATE
from app.dependencies.auth import get_current_active_user, require_master
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.role import Role
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.audit_log import AuditLog
from app.models.gifts_passion import GiftsPassion
from pydantic import BaseModel
from app.schemas.master import (
    SystemStats,
    ChurchListResponse,
    ChurchDetail,
    UserListResponse,
    UserDetail,
    AuditLogListResponse,
    AuditLogEntry,
    ImpersonateRequest,
    ImpersonateResponse,
    SystemExportRequest,
    MasterTransferPrimaryAdminRequest,
)

router = APIRouter(prefix="/master", tags=["Master Admin"])


@router.get("/stats", response_model=SystemStats)
@limiter.limit(MASTER_RATE)
async def get_system_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get system-wide statistics"""
    
    # Total counts
    total_users = db.query(User).count()
    total_churches = db.query(Organization).count()
    total_assessments = db.query(Assessment).filter(
        Assessment.status == "completed"
    ).count()
    
    # Time-based stats
    now = datetime.now(timezone.utc)
    
    # Last 30 days
    thirty_days_ago = now - timedelta(days=30)
    users_30d = db.query(User).filter(User.created_at >= thirty_days_ago).count()
    assessments_30d = db.query(Assessment).filter(
        Assessment.status == "completed",
        Assessment.completed_at >= thirty_days_ago
    ).count()
    
    # Last 90 days
    ninety_days_ago = now - timedelta(days=90)
    users_90d = db.query(User).filter(User.created_at >= ninety_days_ago).count()
    assessments_90d = db.query(Assessment).filter(
        Assessment.status == "completed",
        Assessment.completed_at >= ninety_days_ago
    ).count()
    
    # Last 365 days
    year_ago = now - timedelta(days=365)
    users_365d = db.query(User).filter(User.created_at >= year_ago).count()
    assessments_365d = db.query(Assessment).filter(
        Assessment.status == "completed",
        Assessment.completed_at >= year_ago
    ).count()
    
    # Active churches (have had activity in last 90 days)
    active_churches = db.query(Organization).join(Membership).join(User).join(
        Assessment, Assessment.user_id == User.id
    ).filter(
        Assessment.status == "completed",
        Assessment.completed_at >= ninety_days_ago
    ).distinct().count()
    
    return SystemStats(
        total_users=total_users,
        total_churches=total_churches,
        total_assessments=total_assessments,
        active_churches=active_churches,
        recent_stats={
            "30_days": {
                "new_users": users_30d,
                "assessments": assessments_30d
            },
            "90_days": {
                "new_users": users_90d,
                "assessments": assessments_90d
            },
            "365_days": {
                "new_users": users_365d,
                "assessments": assessments_365d
            }
        }
    )


@router.get("/churches", response_model=ChurchListResponse)
@limiter.limit(MASTER_RATE)
async def get_all_churches(
    request: Request,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get all churches with statistics"""
    
    query = db.query(Organization)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Organization.name.ilike(search_pattern)) |
            (Organization.city.ilike(search_pattern))
        )
    
    total = query.count()
    churches = query.offset((page - 1) * per_page).limit(per_page).all()
    
    result = []
    for church in churches:
        # Get member count
        member_count = db.query(Membership).filter(
            Membership.organization_id == church.id
        ).count()
        
        # Get assessment count
        assessment_count = db.query(Assessment).join(
            Membership, Assessment.user_id == Membership.user_id
        ).filter(
            Membership.organization_id == church.id,
            Assessment.status == "completed"
        ).count()
        
        # Get admins with primary flag
        admin_rows = db.query(User, Membership.is_primary_admin).join(
            Membership, User.id == Membership.user_id
        ).join(Role, Membership.role_id == Role.id).filter(
            Membership.organization_id == church.id,
            Role.name == "admin"
        ).order_by(Membership.is_primary_admin.desc()).all()

        # Last activity
        last_activity = db.query(Assessment.completed_at).join(
            Membership, Assessment.user_id == Membership.user_id
        ).filter(
            Membership.organization_id == church.id,
            Assessment.status == "completed"
        ).order_by(Assessment.completed_at.desc()).first()

        result.append(ChurchDetail(
            id=church.id,
            name=church.name,
            key=church.key,
            city=church.city,
            state=church.state,
            country=church.country,
            status=church.status or "active",
            is_comped=church.is_comped,
            member_count=member_count,
            assessment_count=assessment_count,
            admins=[{"id": a.id, "email": a.email, "name": f"{a.first_name} {a.last_name}", "is_primary": is_primary or False} for a, is_primary in admin_rows],
            last_activity=last_activity[0] if last_activity else None,
            created_at=church.created_at
        ))
    
    return ChurchListResponse(
        churches=result,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/churches/{church_id}", response_model=ChurchDetail)
@limiter.limit(MASTER_RATE)
async def get_church_detail(
    request: Request,
    church_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get detailed information about a church"""
    
    church = db.query(Organization).filter(Organization.id == church_id).first()
    
    if not church:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church not found"
        )
    
    member_count = db.query(Membership).filter(
        Membership.organization_id == church.id
    ).count()
    
    assessment_count = db.query(Assessment).join(
        Membership, Assessment.user_id == Membership.user_id
    ).filter(
        Membership.organization_id == church.id,
        Assessment.status == "completed"
    ).count()

    admin_rows = db.query(User, Membership.is_primary_admin).join(
        Membership, User.id == Membership.user_id
    ).join(Role, Membership.role_id == Role.id).filter(
        Membership.organization_id == church.id,
        Role.name == "admin"
    ).order_by(Membership.is_primary_admin.desc()).all()

    last_activity = db.query(Assessment.completed_at).join(
        Membership, Assessment.user_id == Membership.user_id
    ).filter(
        Membership.organization_id == church.id,
        Assessment.status == "completed"
    ).order_by(Assessment.completed_at.desc()).first()

    return ChurchDetail(
        id=church.id,
        name=church.name,
        key=church.key,
        city=church.city,
        state=church.state,
        country=church.country,
        status=church.status or "active",
        is_comped=church.is_comped,
        member_count=member_count,
        assessment_count=assessment_count,
        admins=[{"id": a.id, "email": a.email, "name": f"{a.first_name} {a.last_name}", "is_primary": is_primary or False} for a, is_primary in admin_rows],
        last_activity=last_activity[0] if last_activity else None,
        created_at=church.created_at
    )


@router.post("/churches/{church_id}/admins/{user_id}")
@limiter.limit(MASTER_RATE)
async def add_church_admin(
    request: Request,
    church_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Add an admin to a church"""
    
    church = db.query(Organization).filter(Organization.id == church_id).first()
    if not church:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church not found"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get or create membership
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.organization_id == church_id
    ).first()
    
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    
    if membership:
        membership.role_id = admin_role.id
        membership.is_primary_admin = False  # Master admin adds secondary admins only
    else:
        membership = Membership(
            user_id=user_id,
            organization_id=church_id,
            role_id=admin_role.id,
            status="active",
            is_primary_admin=False  # Master admin adds secondary admins only
        )
        db.add(membership)
    
    db.commit()
    
    # Log the action
    audit_log = AuditLog(
        user_id=current_user.id,
        action="role_change",
        target_type="user",
        target_id=user_id,
        details={
            "action": "add_admin",
            "organization_id": str(church_id),
            "reason": "Master admin action"
        }
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Admin added successfully"}


@router.delete("/churches/{church_id}/admins/{user_id}")
@limiter.limit(MASTER_RATE)
async def remove_church_admin(
    request: Request,
    church_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Remove an admin from a church"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.organization_id == church_id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )
    
    # Change to member role
    member_role = db.query(Role).filter(Role.name == "member").first()
    membership.role_id = member_role.id
    db.commit()
    
    # Log the action
    audit_log = AuditLog(
        user_id=current_user.id,
        action="role_change",
        target_type="user",
        target_id=user_id,
        details={
            "action": "remove_admin",
            "organization_id": str(church_id),
            "reason": "Master admin action"
        }
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Admin removed successfully"}


@router.post("/churches/{church_id}/transfer-primary-admin")
@limiter.limit(MASTER_RATE)
async def master_transfer_primary_admin(
    request: Request,
    church_id: str,
    body: MasterTransferPrimaryAdminRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Transfer primary admin status to another admin in a church.
    Master admin override — does not require current primary admin's involvement."""

    church = db.query(Organization).filter(Organization.id == church_id).first()
    if not church:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church not found"
        )

    # Get target user's membership in this church
    target_membership = db.query(Membership).filter(
        Membership.user_id == body.new_primary_user_id,
        Membership.organization_id == church_id,
        Membership.status == "active",
    ).first()

    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user is not an active member of this church"
        )

    if target_membership.is_primary_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is already the primary admin"
        )

    # Promote target to admin role if they aren't already
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if target_membership.role_id != admin_role.id:
        target_membership.role_id = admin_role.id

    # Remove primary from current primary admin (if one exists)
    current_primary = db.query(Membership).filter(
        Membership.organization_id == church_id,
        Membership.is_primary_admin == True,
    ).first()

    old_primary_id = None
    if current_primary:
        old_primary_id = str(current_primary.user_id)
        current_primary.is_primary_admin = False

    # Set new primary admin
    target_membership.is_primary_admin = True
    db.commit()

    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="master_transfer_primary_admin",
        target_type="organization",
        target_id=church_id,
        details={
            "organization_id": str(church_id),
            "organization_name": church.name,
            "previous_primary_id": old_primary_id,
            "new_primary_id": str(body.new_primary_user_id),
            "reason": "Master admin override"
        }
    )
    db.add(audit_log)
    db.commit()

    return {"message": "Primary admin transferred successfully"}


@router.get("/users", response_model=UserListResponse)
@limiter.limit(MASTER_RATE)
async def get_all_users(
    request: Request,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get all users with their organization info"""
    
    query = db.query(User)
    
    if search:
        search_pattern = f"%{search}%"
        full_name = func.concat(User.first_name, ' ', User.last_name)
        query = query.filter(
            (User.first_name.ilike(search_pattern)) |
            (User.last_name.ilike(search_pattern)) |
            (User.email.ilike(search_pattern)) |
            (full_name.ilike(search_pattern))
        )
    
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    
    result = []
    for user in users:
        # Get organization info
        membership = db.query(Membership).filter(
            Membership.user_id == user.id
        ).first()
        
        org_info = None
        if membership and membership.organization:
            org_info = {
                "id": membership.organization.id,
                "name": membership.organization.name,
                "role": membership.role.name if membership.role else None
            }
        
        # Get assessment count
        assessment_count = db.query(Assessment).filter(
            Assessment.user_id == user.id,
            Assessment.status == "completed"
        ).count()
        
        result.append(UserDetail(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            status=user.status,
            organization=org_info,
            assessment_count=assessment_count,
            created_at=user.created_at,
            last_login=None  # Would need to track this separately
        ))
    
    return UserListResponse(
        users=result,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/users/{user_id}", response_model=UserDetail)
@limiter.limit(MASTER_RATE)
async def get_user_detail(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get detailed information about a user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    membership = db.query(Membership).filter(
        Membership.user_id == user.id
    ).first()
    
    org_info = None
    if membership and membership.organization:
        org_info = {
            "id": membership.organization.id,
            "name": membership.organization.name,
            "role": membership.role.name if membership.role else None
        }
    
    assessment_count = db.query(Assessment).filter(
        Assessment.user_id == user.id,
        Assessment.status == "completed"
    ).count()
    
    return UserDetail(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        status=user.status,
        organization=org_info,
        assessment_count=assessment_count,
        created_at=user.created_at,
        last_login=None
    )


@router.post("/impersonate", response_model=ImpersonateResponse)
@limiter.limit(MASTER_RATE)
async def impersonate_user(
    http_request: Request,
    request: ImpersonateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """
    Start impersonating a user.
    
    Creates a special impersonation token that:
    - Has a shorter expiration time (15 minutes)
    - Is explicitly marked as an impersonation token
    - Cannot be used for sensitive operations (password changes, billing, etc.)
    - Logs all actions with impersonation context
    """
    
    from app.core.security import create_access_token
    
    target_user = db.query(User).filter(User.id == request.user_id).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent impersonating master admins (additional safety)
    target_membership = db.query(Membership).join(Role).filter(
        Membership.user_id == target_user.id,
        Role.name == "master"
    ).first()
    
    if target_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate master administrators"
        )
    
    # Log the impersonation
    audit_log = AuditLog(
        user_id=current_user.id,
        action="impersonate_start",
        target_type="user",
        target_id=request.user_id,
        details={
            "reason": request.reason,
            "target_email": target_user.email,
            "impersonator_email": current_user.email
        }
    )
    db.add(audit_log)
    db.commit()
    
    # Create a special token for impersonation with explicit flag
    token = create_access_token(
        data={
            "sub": str(target_user.id),
            "impersonated_by": str(current_user.id),
            "impersonation_reason": request.reason
        },
        is_impersonation=True  # Explicitly mark as impersonation token
    )
    
    return ImpersonateResponse(
        token=token,
        user_id=target_user.id,
        email=target_user.email,
        message=f"Impersonating {target_user.email} (token expires in 15 minutes)"
    )


@router.get("/audit-log", response_model=AuditLogListResponse)
@limiter.limit(MASTER_RATE)
async def get_audit_log(
    request: Request,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    target_type: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get audit log entries"""
    
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    
    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    result = []
    for entry in entries:
        user = db.query(User).filter(User.id == entry.user_id).first()
        
        result.append(AuditLogEntry(
            id=entry.id,
            user_id=entry.user_id,
            user_email=user.email if user else "Unknown",
            user_name=f"{user.first_name} {user.last_name}" if user else "Unknown",
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            details=entry.details,
            created_at=entry.created_at
        ))
    
    return AuditLogListResponse(
        entries=result,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/export/{export_type}")
@limiter.limit(EXPORT_RATE)
async def system_export(
    request: Request,
    export_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Export system data as CSV"""
    
    # Log the export
    audit_log = AuditLog(
        user_id=current_user.id,
        action="export",
        target_type="system",
        details={"export_type": export_type}
    )
    db.add(audit_log)
    db.commit()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if export_type == "users":
        writer.writerow(["ID", "Email", "First Name", "Last Name", "Status", "Organization", "Role", "Created At"])
        
        users = db.query(User).all()
        for user in users:
            membership = db.query(Membership).filter(Membership.user_id == user.id).first()
            org_name = membership.organization.name if membership and membership.organization else "Independent"
            role_name = membership.role.name if membership and membership.role else "N/A"
            
            writer.writerow([
                str(user.id),
                user.email,
                user.first_name,
                user.last_name,
                user.status,
                org_name,
                role_name,
                user.created_at.isoformat() if user.created_at else ""
            ])
    
    elif export_type == "assessments":
        writer.writerow(["Assessment ID", "User Email", "Completed At", "Gift 1", "Score 1", "Gift 2", "Score 2", "Style 1", "Score 1", "Style 2", "Score 2"])
        
        assessments = db.query(Assessment, User, AssessmentResult).join(
            User, Assessment.user_id == User.id
        ).outerjoin(
            AssessmentResult, Assessment.id == AssessmentResult.assessment_id
        ).filter(Assessment.status == "completed").all()
        
        for assessment, user, result in assessments:
            gift1_name = ""
            gift2_name = ""
            style1_name = ""
            style2_name = ""
            
            if result:
                gift1 = db.query(GiftsPassion).filter(GiftsPassion.id == result.gift_1_id).first() if result.gift_1_id else None
                gift2 = db.query(GiftsPassion).filter(GiftsPassion.id == result.gift_2_id).first() if result.gift_2_id else None
                style1 = db.query(GiftsPassion).filter(GiftsPassion.id == result.passion_1_id).first() if result.passion_1_id else None
                style2 = db.query(GiftsPassion).filter(GiftsPassion.id == result.passion_2_id).first() if result.passion_2_id else None
                gift1_name = gift1.name if gift1 else ""
                gift2_name = gift2.name if gift2 else ""
                style1_name = style1.name if style1 else ""
                style2_name = style2.name if style2 else ""
            
            writer.writerow([
                str(assessment.id),
                user.email,
                assessment.completed_at.isoformat() if assessment.completed_at else "",
                gift1_name,
                result.spiritual_gift_1_score if result else "",
                gift2_name,
                result.spiritual_gift_2_score if result else "",
                style1_name,
                result.influencing_style_1_score if result else "",
                style2_name,
                result.influencing_style_2_score if result else ""
            ])
    
    elif export_type == "full":
        # Full export - users and their assessments
        writer.writerow(["=== USERS ==="])
        writer.writerow(["ID", "Email", "First Name", "Last Name", "Status", "Organization", "Role", "Created At"])
        
        users = db.query(User).all()
        for user in users:
            membership = db.query(Membership).filter(Membership.user_id == user.id).first()
            org_name = membership.organization.name if membership and membership.organization else "Independent"
            role_name = membership.role.name if membership and membership.role else "N/A"
            
            writer.writerow([
                str(user.id),
                user.email,
                user.first_name,
                user.last_name,
                user.status,
                org_name,
                role_name,
                user.created_at.isoformat() if user.created_at else ""
            ])
        
        writer.writerow([])
        writer.writerow(["=== CHURCHES ==="])
        writer.writerow(["ID", "Name", "Key", "City", "State", "Country", "Created At"])
        
        churches = db.query(Organization).all()
        for church in churches:
            writer.writerow([
                str(church.id),
                church.name,
                church.key,
                church.city or "",
                church.state or "",
                church.country or "",
                church.created_at.isoformat() if church.created_at else ""
            ])
        
        writer.writerow([])
        writer.writerow(["=== ASSESSMENTS ==="])
        writer.writerow(["Assessment ID", "User Email", "Completed At", "Gift 1", "Score 1", "Gift 2", "Score 2", "Style 1", "Score 1", "Style 2", "Score 2"])
        
        assessments = db.query(Assessment, User, AssessmentResult).join(
            User, Assessment.user_id == User.id
        ).outerjoin(
            AssessmentResult, Assessment.id == AssessmentResult.assessment_id
        ).filter(Assessment.status == "completed").all()
        
        for assessment, user, result in assessments:
            gift1_name = ""
            gift2_name = ""
            style1_name = ""
            style2_name = ""
            
            if result:
                gift1 = db.query(GiftsPassion).filter(GiftsPassion.id == result.gift_1_id).first() if result.gift_1_id else None
                gift2 = db.query(GiftsPassion).filter(GiftsPassion.id == result.gift_2_id).first() if result.gift_2_id else None
                style1 = db.query(GiftsPassion).filter(GiftsPassion.id == result.passion_1_id).first() if result.passion_1_id else None
                style2 = db.query(GiftsPassion).filter(GiftsPassion.id == result.passion_2_id).first() if result.passion_2_id else None
                gift1_name = gift1.name if gift1 else ""
                gift2_name = gift2.name if gift2 else ""
                style1_name = style1.name if style1 else ""
                style2_name = style2.name if style2 else ""
            
            writer.writerow([
                str(assessment.id),
                user.email,
                assessment.completed_at.isoformat() if assessment.completed_at else "",
                gift1_name,
                result.spiritual_gift_1_score if result else "",
                gift2_name,
                result.spiritual_gift_2_score if result else "",
                style1_name,
                result.influencing_style_1_score if result else "",
                style2_name,
                result.influencing_style_2_score if result else ""
            ])
        
        writer.writerow([])
        writer.writerow(["=== AUDIT LOG ==="])
        writer.writerow(["ID", "User Email", "Action", "Target Type", "Target ID", "Details", "Created At"])
        
        audit_logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
        for log in audit_logs:
            user = db.query(User).filter(User.id == log.user_id).first()
            writer.writerow([
                str(log.id),
                user.email if user else "System",
                log.action,
                log.target_type or "",
                str(log.target_id) if log.target_id else "",
                str(log.details) if log.details else "",
                log.created_at.isoformat() if log.created_at else ""
            ])
    
    output.seek(0)

    from fastapi import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_{export_type}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"}
    )


class ChurchStatusUpdate(BaseModel):
    status: str  # "active" or "paused"


@router.put("/churches/{church_id}/status")
@limiter.limit(MASTER_RATE)
async def update_church_status(
    church_id: str,
    payload: ChurchStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Pause or restore a church"""

    if payload.status not in ("active", "paused"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'active' or 'paused'"
        )

    org = db.query(Organization).filter(Organization.id == church_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church not found"
        )

    org.status = payload.status
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action=f"church_{payload.status}",
        target_type="organization",
        target_id=org.id,
        details={"church_name": org.name, "new_status": payload.status}
    )
    db.add(audit)
    db.commit()

    return {"message": f"Church {payload.status}", "status": payload.status}


class ChurchCompUpdate(BaseModel):
    is_comped: bool


@router.put("/churches/{church_id}/comp")
@limiter.limit(MASTER_RATE)
async def update_church_comp(
    church_id: str,
    payload: ChurchCompUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Grant or revoke comped access for a church (billed elsewhere, bypasses Stripe)"""

    org = db.query(Organization).filter(Organization.id == church_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church not found"
        )

    old_value = org.is_comped
    org.is_comped = payload.is_comped
    db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action="church_comp_toggle",
        target_type="organization",
        target_id=org.id,
        details={
            "church_name": org.name,
            "is_comped_before": old_value,
            "is_comped_after": payload.is_comped,
        }
    )
    db.add(audit)
    db.commit()

    action = "granted" if payload.is_comped else "revoked"
    return {"is_comped": payload.is_comped, "message": f"Comped access {action} for {org.name}"}


@router.get("/dashboard-stats")
@limiter.limit(MASTER_RATE)
async def get_dashboard_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get monthly aggregated stats for dashboard charts"""

    now = datetime.now(timezone.utc)
    current_year = now.year
    year_start = datetime(current_year, 1, 1, tzinfo=timezone.utc)

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # GPS Completed Assessments by month
    gps_monthly = []
    for month_idx in range(1, 13):
        month_start = datetime(current_year, month_idx, 1, tzinfo=timezone.utc)
        if month_idx < 12:
            month_end = datetime(current_year, month_idx + 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)

        count = db.query(Assessment).filter(
            Assessment.status == "completed",
            Assessment.completed_at >= month_start,
            Assessment.completed_at < month_end
        ).count()

        gps_monthly.append({"month": months[month_idx - 1], "count": count})

    # Total Users by month (created_at)
    users_monthly = []
    for month_idx in range(1, 13):
        month_start = datetime(current_year, month_idx, 1, tzinfo=timezone.utc)
        if month_idx < 12:
            month_end = datetime(current_year, month_idx + 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)

        count = db.query(User).filter(
            User.created_at >= month_start,
            User.created_at < month_end
        ).count()

        users_monthly.append({"month": months[month_idx - 1], "count": count})

    # Total Organizations by month (created_at)
    orgs_monthly = []
    for month_idx in range(1, 13):
        month_start = datetime(current_year, month_idx, 1, tzinfo=timezone.utc)
        if month_idx < 12:
            month_end = datetime(current_year, month_idx + 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)

        count = db.query(Organization).filter(
            Organization.created_at >= month_start,
            Organization.created_at < month_end
        ).count()

        orgs_monthly.append({"month": months[month_idx - 1], "count": count})

    return {
        "gps_assessments_monthly": gps_monthly,
        "myimpact_assessments_monthly": [],  # Not yet implemented
        "users_monthly": users_monthly,
        "orgs_monthly": orgs_monthly
    }
