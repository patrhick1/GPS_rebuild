"""
Master Admin API endpoints
Full system access for master administrators
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import csv
import io

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user, require_master
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.role import Role
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.audit_log import AuditLog
from app.models.gifts_passion import GiftsPassion
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
)

router = APIRouter(prefix="/master", tags=["Master Admin"])


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
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
    now = datetime.utcnow()
    
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
    active_churches = db.query(Organization).join(Membership).join(User).join(Assessment).filter(
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
async def get_all_churches(
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get all churches with statistics"""
    
    query = db.query(Organization)
    
    if search:
        query = query.filter(
            (Organization.name.ilike(f"%{search}%")) |
            (Organization.city.ilike(f"%{search}%"))
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
        assessment_count = db.query(Assessment).join(Membership).filter(
            Membership.organization_id == church.id,
            Assessment.status == "completed"
        ).count()
        
        # Get admins
        admins = db.query(User).join(Membership).join(Role).filter(
            Membership.organization_id == church.id,
            Role.name == "admin"
        ).all()
        
        # Last activity
        last_activity = db.query(Assessment.completed_at).join(Membership).filter(
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
            member_count=member_count,
            assessment_count=assessment_count,
            admins=[{"id": a.id, "email": a.email, "name": f"{a.first_name} {a.last_name}"} for a in admins],
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
async def get_church_detail(
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
    
    assessment_count = db.query(Assessment).join(Membership).filter(
        Membership.organization_id == church.id,
        Assessment.status == "completed"
    ).count()
    
    admins = db.query(User).join(Membership).join(Role).filter(
        Membership.organization_id == church.id,
        Role.name == "admin"
    ).all()
    
    last_activity = db.query(Assessment.completed_at).join(Membership).filter(
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
        member_count=member_count,
        assessment_count=assessment_count,
        admins=[{"id": a.id, "email": a.email, "name": f"{a.first_name} {a.last_name}"} for a in admins],
        last_activity=last_activity[0] if last_activity else None,
        created_at=church.created_at
    )


@router.post("/churches/{church_id}/admins/{user_id}")
async def add_church_admin(
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
    else:
        membership = Membership(
            user_id=user_id,
            organization_id=church_id,
            role_id=admin_role.id,
            status="active"
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
async def remove_church_admin(
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


@router.get("/users", response_model=UserListResponse)
async def get_all_users(
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Get all users with their organization info"""
    
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
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
async def get_user_detail(
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
async def impersonate_user(
    request: ImpersonateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_master)
):
    """Start impersonating a user"""
    
    from app.core.security import create_access_token
    
    target_user = db.query(User).filter(User.id == request.user_id).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log the impersonation
    audit_log = AuditLog(
        user_id=current_user.id,
        action="impersonate",
        target_type="user",
        target_id=request.user_id,
        details={
            "reason": request.reason,
            "target_email": target_user.email
        }
    )
    db.add(audit_log)
    db.commit()
    
    # Create a special token for impersonation
    token = create_access_token(
        data={
            "sub": str(target_user.id),
            "impersonated_by": str(current_user.id),
            "impersonation_reason": request.reason
        }
    )
    
    return ImpersonateResponse(
        token=token,
        user_id=target_user.id,
        email=target_user.email,
        message=f"Impersonating {target_user.email}"
    )


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
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
async def system_export(
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
        headers={"Content-Disposition": f"attachment; filename=export_{export_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )
