"""
Dashboard API endpoints for user-facing dashboard features
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response, Query
from sqlalchemy.orm import Session
from datetime import datetime
import csv
import io

from app.core.database import get_db
from app.core.rate_limits import limiter, AUTHENTICATED_RATE
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.myimpact_result import MyImpactResult
from app.models.gifts_passion import GiftsPassion
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.question import Question
from app.models.answer import Answer
from app.schemas.dashboard import (
    DashboardSummary,
    AssessmentHistoryItem,
    AssessmentDetail,
    ComparisonRequest,
    ComparisonResult,
    ChurchSearchResult,
    LinkRequestCreate,
    LinkRequestResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
@limiter.limit(AUTHENTICATED_RATE)
async def get_dashboard_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dashboard summary for current user"""
    
    # Get most recent completed assessment
    latest_assessment = db.query(Assessment).filter(
        Assessment.user_id == current_user.id,
        Assessment.status == "completed"
    ).order_by(Assessment.completed_at.desc()).first()
    
    latest_result = None
    if latest_assessment:
        latest_result = db.query(AssessmentResult).filter(
            AssessmentResult.assessment_id == latest_assessment.id
        ).first()
    
    # Get assessment counts
    total_count = db.query(Assessment).filter(
        Assessment.user_id == current_user.id,
        Assessment.status == "completed"
    ).count()
    
    # Get organization info (only for active memberships)
    organization = None
    pending_organization = None
    if current_user.memberships:
        membership = next(
            (m for m in current_user.memberships if m.organization_id is not None and m.status == "active"),
            None,
        )
        if membership and membership.organization:
            organization = {
                "id": membership.organization.id,
                "name": membership.organization.name,
                "role": membership.role.name if membership.role else None,
                "is_primary_admin": membership.is_primary_admin if membership.role and membership.role.name == "admin" else False
            }
        else:
            # Check for pending or declined membership
            pending_membership = next(
                (m for m in current_user.memberships if m.organization_id is not None and m.status in ("pending", "declined")),
                None,
            )
            if pending_membership and pending_membership.organization:
                pending_organization = {
                    "id": pending_membership.organization.id,
                    "name": pending_membership.organization.name,
                    "status": pending_membership.status,
                }

    return DashboardSummary(
        user={
            "id": current_user.id,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email
        },
        latest_assessment={
            "id": latest_assessment.id,
            "completed_at": latest_assessment.completed_at,
            "top_gifts": _get_top_gifts_detail(db, latest_result) if latest_result else None,
            "top_passions": _get_top_passions_detail(db, latest_result) if latest_result else None
        } if latest_assessment else None,
        stats={
            "total_assessments": total_count,
            "has_organization": organization is not None
        },
        organization=organization,
        pending_organization=pending_organization
    )


@router.get("/assessments", response_model=List[AssessmentHistoryItem])
@limiter.limit(AUTHENTICATED_RATE)
async def get_assessment_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    instrument_type: Optional[str] = Query(None, description="Filter by instrument type: 'gps' or 'myimpact'"),
    include_in_progress: bool = True,
    limit: int = 50,
    offset: int = 0
):
    """Get assessment history for current user"""

    query = db.query(Assessment).filter(
        Assessment.user_id == current_user.id
    )
    
    # Filter by instrument type if provided
    if instrument_type:
        query = query.filter(Assessment.instrument_type == instrument_type)
    
    if include_in_progress:
        query = query.filter(Assessment.status.in_(["completed", "in_progress"]))
    else:
        query = query.filter(Assessment.status == "completed")

    assessments = query.order_by(Assessment.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for assessment in assessments:
        # Compute progress percentage based on instrument type
        if assessment.status == "completed":
            progress_percentage = 100
        else:
            # Get question count for this instrument type
            question_count = db.query(Question).filter(
                Question.instrument_type == assessment.instrument_type
            ).count()
            
            if question_count > 0:
                answer_count = db.query(Answer).filter(
                    Answer.assessment_id == assessment.id
                ).count()
                progress_percentage = round((answer_count / question_count) * 100)
            else:
                progress_percentage = 0

        # Get results based on instrument type
        if assessment.instrument_type == "myimpact":
            myimpact_result = db.query(MyImpactResult).filter(
                MyImpactResult.assessment_id == assessment.id
            ).first()
            
            result.append(AssessmentHistoryItem(
                id=assessment.id,
                status=assessment.status,
                instrument_type=assessment.instrument_type,
                completed_at=assessment.completed_at,
                created_at=assessment.created_at,
                progress_percentage=progress_percentage,
                top_gifts=[],
                top_passions=[],
                myimpact_score=myimpact_result.myimpact_score if myimpact_result else None,
                character_score=myimpact_result.character_score if myimpact_result else None,
                calling_score=myimpact_result.calling_score if myimpact_result else None
            ))
        else:
            # GPS assessment
            assessment_result = db.query(AssessmentResult).filter(
                AssessmentResult.assessment_id == assessment.id
            ).first()

            result.append(AssessmentHistoryItem(
                id=assessment.id,
                status=assessment.status,
                instrument_type=assessment.instrument_type,
                completed_at=assessment.completed_at,
                created_at=assessment.created_at,
                progress_percentage=progress_percentage,
                top_gifts=_get_top_gifts_summary(db, assessment_result) if assessment_result else [],
                top_passions=_get_top_passions_summary(db, assessment_result) if assessment_result else [],
                myimpact_score=None,
                character_score=None,
                calling_score=None
            ))

    return result


@router.get("/assessments/{assessment_id}", response_model=AssessmentDetail)
@limiter.limit(AUTHENTICATED_RATE)
async def get_assessment_detail(
    request: Request,
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed view of a specific assessment"""
    try:
        assessment_uuid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assessment ID format"
        )
    
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_uuid,
        Assessment.user_id == current_user.id
    ).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    result = db.query(AssessmentResult).filter(
        AssessmentResult.assessment_id == assessment.id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment results not found"
        )
    
    return AssessmentDetail(
        id=assessment.id,
        completed_at=assessment.completed_at,
        created_at=assessment.created_at,
        gifts=_get_all_gifts_detail(db, result),
        passions=_get_all_passions_detail(db, result),
        selections={
            "people": result.people.split(',') if result.people else [],
            "causes": result.cause.split(',') if result.cause else [],
            "abilities": result.abilities.split(',') if result.abilities else []
        },
        stories={
            "gift": result.story_gift_answer,
            "ability": result.story_ability_answer,
            "passion": result.story_passion_answer,
            "influencing": result.story_influencing_answer,
            "onechange": result.story_onechange_answer,
            "closestpeople": result.story_closestpeople_answer,
            "oneregret": result.story_oneregret_answer
        }
    )


@router.post("/compare", response_model=ComparisonResult)
@limiter.limit(AUTHENTICATED_RATE)
async def compare_assessments(
    request: Request,
    comparison: ComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Compare two assessments side by side"""
    
    # Verify both assessments belong to user
    assessment1 = db.query(Assessment).filter(
        Assessment.id == comparison.assessment_id_1,
        Assessment.user_id == current_user.id,
        Assessment.status == "completed"
    ).first()
    
    assessment2 = db.query(Assessment).filter(
        Assessment.id == comparison.assessment_id_2,
        Assessment.user_id == current_user.id,
        Assessment.status == "completed"
    ).first()
    
    if not assessment1 or not assessment2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both assessments not found"
        )
    
    result1 = db.query(AssessmentResult).filter(
        AssessmentResult.assessment_id == assessment1.id
    ).first()
    
    result2 = db.query(AssessmentResult).filter(
        AssessmentResult.assessment_id == assessment2.id
    ).first()
    
    return ComparisonResult(
        assessment_1={
            "id": assessment1.id,
            "completed_at": assessment1.completed_at,
            "gifts": _get_all_gifts_detail(db, result1) if result1 else [],
            "passions": _get_all_passions_detail(db, result1) if result1 else []
        },
        assessment_2={
            "id": assessment2.id,
            "completed_at": assessment2.completed_at,
            "gifts": _get_all_gifts_detail(db, result2) if result2 else [],
            "passions": _get_all_passions_detail(db, result2) if result2 else []
        }
    )


@router.get("/export/csv")
@limiter.limit(AUTHENTICATED_RATE)
async def export_assessments_csv(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export user's assessment history as CSV"""
    
    assessments = db.query(Assessment).filter(
        Assessment.user_id == current_user.id,
        Assessment.status == "completed"
    ).order_by(Assessment.completed_at.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Assessment Date",
        "Gift 1",
        "Score 1",
        "Gift 2",
        "Score 2",
        "Passion 1",
        "Score 1",
        "Passion 2",
        "Score 2"
    ])
    
    # Write data
    for assessment in assessments:
        result = db.query(AssessmentResult).filter(
            AssessmentResult.assessment_id == assessment.id
        ).first()
        
        if result:
            # Get gift names
            gift1 = db.query(GiftsPassion).filter(GiftsPassion.id == result.gift_1_id).first()
            gift2 = db.query(GiftsPassion).filter(GiftsPassion.id == result.gift_2_id).first()
            passion1 = db.query(GiftsPassion).filter(GiftsPassion.id == result.passion_1_id).first()
            passion2 = db.query(GiftsPassion).filter(GiftsPassion.id == result.passion_2_id).first()
            
            writer.writerow([
                assessment.completed_at.isoformat() if assessment.completed_at else "",
                gift1.name if gift1 else "",
                result.spiritual_gift_1_score or "",
                gift2.name if gift2 else "",
                result.spiritual_gift_2_score or "",
                passion1.name if passion1 else "",
                result.passion_1_score or "",
                passion2.name if passion2 else "",
                result.passion_2_score or ""
            ])
    
    # Prepare response
    output.seek(0)
    filename = f"gps_assessments_{current_user.email}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Helper functions
def _get_top_gifts_detail(db: Session, result: AssessmentResult):
    """Get detailed info for top gifts"""
    gifts = []
    for gift_id, score in [
        (result.gift_1_id, result.spiritual_gift_1_score),
        (result.gift_2_id, result.spiritual_gift_2_score)
    ]:
        if gift_id:
            gift = db.query(GiftsPassion).filter(GiftsPassion.id == gift_id).first()
            if gift:
                gifts.append({
                    "id": gift.id,
                    "name": gift.name,
                    "short_code": gift.short_code,
                    "score": score,
                    "description": gift.description
                })
    return gifts


def _get_top_passions_detail(db: Session, result: AssessmentResult):
    """Get detailed info for top passions"""
    passions = []
    for passion_id, score in [
        (result.passion_1_id, result.passion_1_score),
        (result.passion_2_id, result.passion_2_score)
    ]:
        if passion_id:
            passion = db.query(GiftsPassion).filter(GiftsPassion.id == passion_id).first()
            if passion:
                passions.append({
                    "id": passion.id,
                    "name": passion.name,
                    "short_code": passion.short_code,
                    "score": score,
                    "description": passion.description
                })
    return passions


def _get_top_gifts_summary(db: Session, result: AssessmentResult):
    """Get summary for top gifts"""
    gifts = []
    for gift_id, score in [
        (result.gift_1_id, result.spiritual_gift_1_score),
        (result.gift_2_id, result.spiritual_gift_2_score)
    ]:
        if gift_id:
            gift = db.query(GiftsPassion).filter(GiftsPassion.id == gift_id).first()
            if gift:
                gifts.append({
                    "name": gift.name,
                    "short_code": gift.short_code,
                    "score": score
                })
    return gifts


def _get_top_passions_summary(db: Session, result: AssessmentResult):
    """Get summary for top passions"""
    passions = []
    for passion_id, score in [
        (result.passion_1_id, result.passion_1_score),
        (result.passion_2_id, result.passion_2_score)
    ]:
        if passion_id:
            passion = db.query(GiftsPassion).filter(GiftsPassion.id == passion_id).first()
            if passion:
                passions.append({
                    "name": passion.name,
                    "short_code": passion.short_code,
                    "score": score
                })
    return passions


def _get_all_gifts_detail(db: Session, result: AssessmentResult):
    """Get all gifts with scores from a result"""
    gifts = []
    for gift_id, score in [
        (result.gift_1_id, result.spiritual_gift_1_score),
        (result.gift_2_id, result.spiritual_gift_2_score),
        (result.gift_3_id, result.spiritual_gift_3_score),
        (result.gift_4_id, result.spiritual_gift_4_score)
    ]:
        if gift_id and score:
            gift = db.query(GiftsPassion).filter(GiftsPassion.id == gift_id).first()
            if gift:
                gifts.append({
                    "id": gift.id,
                    "name": gift.name,
                    "short_code": gift.short_code,
                    "score": score
                })
    return gifts


def _get_all_passions_detail(db: Session, result: AssessmentResult):
    """Get all passions with scores from a result"""
    passions = []
    for passion_id, score in [
        (result.passion_1_id, result.passion_1_score),
        (result.passion_2_id, result.passion_2_score),
        (result.passion_3_id, result.passion_3_score)
    ]:
        if passion_id and score:
            passion = db.query(GiftsPassion).filter(GiftsPassion.id == passion_id).first()
            if passion:
                passions.append({
                    "id": passion.id,
                    "name": passion.name,
                    "short_code": passion.short_code,
                    "score": score
                })
    return passions


# Admin Upgrade Endpoint

@router.post("/upgrade-to-admin")
@limiter.limit(AUTHENTICATED_RATE)
async def upgrade_to_admin(
    request: Request,
    church_name: str,
    city: str,
    state: Optional[str] = None,
    country: str = "USA",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upgrade user to church admin by creating a new organization"""
    
    # Check if user is already associated with an organization
    existing_membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.organization_id != None
    ).first()
    
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already associated with an organization"
        )
    
    # Generate unique key for the organization
    import re
    base_key = re.sub(r'[^a-zA-Z0-9]+', '-', church_name.lower()).strip('-')
    key = base_key
    counter = 1
    
    # Ensure key is unique
    while db.query(Organization).filter(Organization.key == key).first():
        key = f"{base_key}-{counter}"
        counter += 1
    
    # Create new organization
    organization = Organization(
        name=church_name,
        city=city,
        state=state,
        country=country,
        key=key,
    )
    db.add(organization)
    db.flush()  # Get organization ID
    
    # Get admin role
    from app.models.role import Role
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin role not found"
        )
    
    # Create or update membership as primary admin
    existing_user_membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if existing_user_membership:
        existing_user_membership.organization_id = organization.id
        existing_user_membership.role_id = admin_role.id
        existing_user_membership.is_primary_admin = True
        existing_user_membership.status = "active"
    else:
        membership = Membership(
            user_id=current_user.id,
            organization_id=organization.id,
            role_id=admin_role.id,
            is_primary_admin=True,  # First admin is primary
            status="active"
        )
        db.add(membership)
    
    db.commit()
    
    return {
        "message": "Successfully upgraded to church admin",
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "key": organization.key,
            "city": organization.city,
            "state": organization.state,
            "country": organization.country,
        },
        "is_primary_admin": True
    }


# Church Linking Endpoints

@router.get("/churches/search", response_model=List[ChurchSearchResult])
@limiter.limit(AUTHENTICATED_RATE)
async def search_churches(
    request: Request,
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search for churches to link to"""
    
    search_pattern = f"%{query}%"
    churches = db.query(Organization).filter(
        Organization.name.ilike(search_pattern)
    ).limit(10).all()
    
    result = []
    for church in churches:
        member_count = db.query(Membership).filter(
            Membership.organization_id == church.id
        ).count()
        
        result.append(ChurchSearchResult(
            id=church.id,
            name=church.name,
            city=church.city,
            state=church.state,
            member_count=member_count
        ))
    
    return result


@router.post("/link-request", response_model=LinkRequestResponse)
@limiter.limit(AUTHENTICATED_RATE)
async def request_church_link(
    request: Request,
    link_data: LinkRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Request to link to a church"""

    # Check if user already has a membership
    existing = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()

    if existing and existing.organization_id and existing.status in ("active", "pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already linked to an organization"
        )

    # Get the organization
    org = db.query(Organization).filter(Organization.id == link_data.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Create or update membership with pending status
    if existing:
        existing.organization_id = link_data.organization_id
        existing.status = "pending"
        membership = existing
    else:
        # Get the member role
        from app.models.role import Role
        member_role = db.query(Role).filter(Role.name == "member").first()

        membership = Membership(
            user_id=current_user.id,
            organization_id=link_data.organization_id,
            role_id=member_role.id if member_role else None,
            status="pending"
        )
        db.add(membership)

    db.commit()

    return LinkRequestResponse(
        id=membership.id,
        organization_id=org.id,
        organization_name=org.name,
        status="pending",
        created_at=membership.created_at
    )


@router.post("/leave-organization")
@limiter.limit(AUTHENTICATED_RATE)
async def leave_organization(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Leave current organization and become independent"""
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership or not membership.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not linked to any organization"
        )

    if membership.is_primary_admin:
        from app.models.membership import Membership as MembershipModel
        from app.models.role import Role as RoleModel

        other_admins = db.query(MembershipModel).filter(
            MembershipModel.organization_id == membership.organization_id,
            MembershipModel.user_id != current_user.id,
            MembershipModel.role.has(name="admin"),
            MembershipModel.status == "active",
        ).count()

        if other_admins > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must transfer primary admin status to another administrator before leaving."
            )

        other_members = db.query(MembershipModel).filter(
            MembershipModel.organization_id == membership.organization_id,
            MembershipModel.user_id != current_user.id,
            MembershipModel.status == "active",
        ).count()

        if other_members > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must promote a member to administrator and transfer primary status before leaving."
            )

        # Alone — cancel the Stripe subscription before leaving
        from app.models.subscription import Subscription
        from app.services.stripe_service import stripe_service
        old_sub = db.query(Subscription).filter(
            Subscription.organization_id == membership.organization_id
        ).order_by(Subscription.created_at.desc()).first()
        if old_sub and old_sub.stripe_subscription_id and old_sub.status not in ("canceled", "incomplete_expired"):
            try:
                stripe_service.cancel_subscription(old_sub.stripe_subscription_id, at_period_end=False)
                old_sub.status = "canceled"
                db.flush()
            except Exception:
                pass

    # Set organization to null (become independent)
    membership.organization_id = None
    membership.status = "active"
    db.commit()

    return {"message": "Successfully left organization"}
