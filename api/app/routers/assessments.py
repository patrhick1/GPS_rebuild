import logging
import uuid
from typing import List, Optional
from io import BytesIO

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.rate_limits import limiter, AUTHENTICATED_RATE
from app.core.sanitization import sanitize_user_input
from app.core.audit import audit_action
from app.dependencies.auth import get_current_active_user, require_admin
from app.models.user import User
from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.question import Question
from app.models.assessment_result import AssessmentResult
from app.models.myimpact_result import MyImpactResult
from app.models.gifts_passion import GiftsPassion
from app.services.scoring_service import ScoringService
from app.services.myimpact_scoring_service import MyImpactScoringService
from app.services.pdf_service import generate_pdf
from app.services.email_service import (
    send_assessment_notification_email,
    send_gps_result_email,
    send_myimpact_result_email,
)
from app.models.membership import Membership
from app.core.config import settings
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentResponse,
    AssessmentWithAnswers,
    AssessmentSubmit,
    AssessmentResultWithDetails,
    QuestionForAssessment,
    AssessmentFormData,
    GradedAssessmentResponse,
    MyImpactResultResponse,
    GradedMyImpactResponse,
)

router = APIRouter(prefix="/assessments", tags=["Assessments"])


def _notify_org_admins(db: Session, current_user: User, assessment: Assessment) -> None:
    """Send assessment completion notification to all admins in the user's org (non-fatal)."""
    try:
        member_membership = db.query(Membership).filter(
            Membership.user_id == current_user.id,
            Membership.status == "active",
        ).first()
        if not member_membership or not member_membership.organization_id:
            return
        admin_memberships = (
            db.query(Membership)
            .filter(
                Membership.organization_id == member_membership.organization_id,
                Membership.status == "active",
                Membership.role.has(name="admin"),
            )
            .options(joinedload(Membership.user))
            .all()
        )
        member_name = f"{current_user.first_name} {current_user.last_name}".strip()
        org_name = member_membership.organization.name
        dashboard_url = f"{settings.FRONTEND_URL}/admin"
        for am in admin_memberships:
            send_assessment_notification_email(
                to_email=am.user.email,
                admin_name=am.user.first_name,
                member_name=member_name,
                org_name=org_name,
                instrument_type=assessment.instrument_type,
                dashboard_url=dashboard_url,
            )
    except Exception as exc:
        logger.error("Failed to notify org admins: %s", exc)


@router.post("/start", response_model=AssessmentFormData, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTHENTICATED_RATE)
async def start_assessment(
    request: Request,
    response: Response,
    instrument_type: str = Query("gps", description="Assessment instrument type: 'gps' or 'myimpact'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Start a new assessment and return the form data"""
    # Validate instrument type
    if instrument_type not in ["gps", "myimpact"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid instrument_type. Must be 'gps' or 'myimpact'."
        )

    # Check for existing in-progress assessment of this type
    existing = db.query(Assessment).filter(
        Assessment.user_id == current_user.id,
        Assessment.instrument_type == instrument_type,
        Assessment.status == "in_progress"
    ).order_by(Assessment.created_at.desc()).first()

    if existing:
        response.status_code = status.HTTP_200_OK
        assessment = existing
    else:
        # Create new assessment
        assessment = Assessment(
            user_id=current_user.id,
            instrument_type=instrument_type,
            status="in_progress"
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
    
    # Get questions filtered by instrument type, eagerly load type relationships
    questions = db.query(Question).filter(
        Question.instrument_type == instrument_type
    ).options(
        joinedload(Question.type),
        joinedload(Question.question_type),
    ).all()

    # Sort questions in correct assessment flow order
    if instrument_type == "gps":
        def gps_sort_key(q):
            type_name = q.type.name if q.type else ""
            qtype_name = q.question_type.type if q.question_type else ""
            passion = q.passion_type or ""

            if type_name == "Spiritual Gift" and qtype_name == "likert":
                return (0, q.order)
            elif type_name == "Spiritual Gift" and qtype_name == "multiple_choice":
                return (1, q.order)  # Abilities (Q166)
            elif type_name == "Influencing Style" and qtype_name == "multiple_choice" and passion == "People":
                return (2, q.order)
            elif type_name == "Influencing Style" and qtype_name == "multiple_choice" and passion == "Cause":
                return (3, q.order)
            elif type_name == "Influencing Style" and qtype_name == "likert":
                return (4, q.order)
            elif type_name == "Story":
                return (5, q.order)
            else:
                return (6, q.order)

        questions = sorted(questions, key=gps_sort_key)
    else:
        questions = sorted(questions, key=lambda q: q.order)

    return AssessmentFormData(
        assessment_id=assessment.id,
        instrument_type=instrument_type,
        questions=[
            QuestionForAssessment(
                id=q.id,
                question=q.question,
                question_es=q.question_es,
                order=q.order,
                type_id=q.type_id,
                question_type_id=q.question_type_id,
                passion_type=q.passion_type,
                default_text=q.default_text,
                summary=q.summary,
                section=q.section,
                question_type_name=q.question_type.type if q.question_type else None,
                type_name=q.type.name if q.type else None,
            )
            for q in questions
        ],
        progress={
            "total_questions": len(questions),
            "answered": 0,
            "remaining": len(questions)
        }
    )


@router.post("/{assessment_id}/save-progress", response_model=AssessmentResponse)
@limiter.limit(AUTHENTICATED_RATE)
async def save_progress(
    request: Request,
    assessment_id: str,
    submit_data: AssessmentSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Save assessment progress (answers) without completing"""
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
    
    if assessment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify completed assessment"
        )
    
    # Save/update answers
    for answer_data in submit_data.answers:
        # Check if answer already exists
        existing = db.query(Answer).filter(
            Answer.assessment_id == assessment_uuid,
            Answer.question_id == answer_data.question_id
        ).first()
        
        if existing:
            # Update existing
            existing.multiple_choice_answer = answer_data.multiple_choice_answer
            existing.numeric_value = answer_data.numeric_value
            existing.text_value = sanitize_user_input(answer_data.text_value)
        else:
            # Create new
            answer = Answer(
                assessment_id=assessment_uuid,
                question_id=answer_data.question_id,
                user_id=current_user.id,
                multiple_choice_answer=answer_data.multiple_choice_answer,
                numeric_value=answer_data.numeric_value,
                text_value=sanitize_user_input(answer_data.text_value)
            )
            db.add(answer)
    
    db.commit()
    db.refresh(assessment)
    
    return assessment


@router.post("/{assessment_id}/submit")
@limiter.limit(AUTHENTICATED_RATE)
@audit_action("assessment_submitted", "assessment")
async def submit_assessment(
    request: Request,
    assessment_id: str,
    submit_data: AssessmentSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit assessment and get results"""
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
    
    if assessment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment already completed"
        )
    
    # Save all answers
    for answer_data in submit_data.answers:
        existing = db.query(Answer).filter(
            Answer.assessment_id == assessment_uuid,
            Answer.question_id == answer_data.question_id
        ).first()
        
        if existing:
            existing.multiple_choice_answer = answer_data.multiple_choice_answer
            existing.numeric_value = answer_data.numeric_value
            existing.text_value = sanitize_user_input(answer_data.text_value)
        else:
            answer = Answer(
                assessment_id=assessment_uuid,
                question_id=answer_data.question_id,
                user_id=current_user.id,
                multiple_choice_answer=answer_data.multiple_choice_answer,
                numeric_value=answer_data.numeric_value,
                text_value=sanitize_user_input(answer_data.text_value)
            )
            db.add(answer)
    
    # Save answers first (don't mark completed yet)
    db.commit()

    # Route to correct scoring service based on instrument type
    # Score FIRST, only mark completed if scoring succeeds
    if assessment.instrument_type == "myimpact":
        scoring_service = MyImpactScoringService(db)

        # Validate all questions answered
        validation = scoring_service.validate_answers(assessment)
        if not validation['is_valid']:
            print(f"MyImpact assessment {assessment_id} submitted with {validation['missing_count']} missing answers")

        # Create MyImpact results
        result = scoring_service.create_result(assessment)

        # Mark as completed only after scoring succeeds
        assessment.status = "completed"
        assessment.completed_at = datetime.now(timezone.utc)
        db.commit()

        response = build_myimpact_result_response(result)
        _notify_org_admins(db, current_user, assessment)
        try:
            send_myimpact_result_email(
                current_user.email,
                current_user.first_name,
                response,
                results_url=f"{settings.FRONTEND_URL}/myimpact-results?id={assessment.id}",
            )
        except Exception as exc:
            logger.error("Failed to send MyImpact result email to %s: %s", current_user.email, exc)
        return response
    else:
        # GPS assessment
        scoring_service = ScoringService(db)

        # Validate all questions answered
        validation = scoring_service.validate_answers(assessment)
        if not validation['is_valid']:
            print(f"GPS assessment {assessment_id} submitted with {validation['missing_count']} missing answers")

        # Create GPS results
        result = scoring_service.create_assessment_result(assessment)

        # Mark as completed only after scoring succeeds
        assessment.status = "completed"
        assessment.completed_at = datetime.now(timezone.utc)
        db.commit()

        response = build_result_with_details(db, result)
        _notify_org_admins(db, current_user, assessment)
        try:
            send_gps_result_email(
                current_user.email,
                current_user.first_name,
                response,
                results_url=f"{settings.FRONTEND_URL}/assessment-results?id={assessment.id}",
            )
        except Exception as exc:
            logger.error("Failed to send GPS result email to %s: %s", current_user.email, exc)
        return response


@router.get("/{assessment_id}/results")
@limiter.limit(AUTHENTICATED_RATE)
async def get_assessment_results(
    request: Request,
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get results for a completed assessment"""
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
    
    if assessment.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment not yet completed"
        )
    
    # Route to correct result fetcher based on instrument type
    if assessment.instrument_type == "myimpact":
        result = db.query(MyImpactResult).filter(
            MyImpactResult.assessment_id == assessment_uuid
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MyImpact results not found"
            )
        
        return build_myimpact_result_response(result)
    else:
        result = db.query(AssessmentResult).filter(
            AssessmentResult.assessment_id == assessment_uuid
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPS results not found"
            )
        
        return build_result_with_details(db, result)


@router.get("/{assessment_id}/grade")
@limiter.limit(AUTHENTICATED_RATE)
async def grade_assessment_preview(
    request: Request,
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Preview grade calculation without saving results"""
    try:
        assessment_uuid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assessment ID format"
        )

    # First try: user's own assessment
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_uuid,
        Assessment.user_id == current_user.id
    ).first()

    # Second try: admin viewing a member's assessment
    if not assessment:
        from app.models.membership import Membership
        admin_membership = db.query(Membership).filter(
            Membership.user_id == current_user.id,
            Membership.role.has(name="admin")
        ).first()
        if admin_membership:
            assessment = db.query(Assessment).filter(
                Assessment.id == assessment_uuid
            ).first()
            # Verify the assessment owner belongs to the admin's org
            if assessment:
                member_membership = db.query(Membership).filter(
                    Membership.user_id == assessment.user_id,
                    Membership.organization_id == admin_membership.organization_id
                ).first()
                if not member_membership:
                    assessment = None

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
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
                {
                    "id": g.id,
                    "name": g.name,
                    "short_code": g.short_code,
                    "description": g.description,
                    "points": g.points
                }
                for g in graded.gifts
            ],
            top_gifts=[
                {
                    "id": g.id,
                    "name": g.name,
                    "short_code": g.short_code,
                    "description": g.description,
                    "points": g.points
                }
                for g in graded.top_gifts
            ],
            passions=[
                {
                    "id": p.id,
                    "name": p.name,
                    "short_code": p.short_code,
                    "description": p.description,
                    "points": p.points
                }
                for p in graded.passions
            ],
            top_passions=[
                {
                    "id": p.id,
                    "name": p.name,
                    "short_code": p.short_code,
                    "description": p.description,
                    "points": p.points
                }
                for p in graded.top_passions
            ],
            abilities=graded.abilities,
            people=graded.people,
            causes=graded.causes,
            stories=[
                {
                    "question": s.question,
                    "answer": s.answer,
                    "question_es": s.question_es
                }
                for s in graded.stories
            ]
        )


@router.get("/{assessment_id}/pdf")
@limiter.limit(AUTHENTICATED_RATE)
async def download_assessment_pdf(
    request: Request,
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download a completed GPS assessment as a PDF report."""
    try:
        assessment_uuid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assessment ID format"
        )

    # First try: user's own assessment
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_uuid,
        Assessment.user_id == current_user.id
    ).first()

    # Second try: admin viewing a member's assessment
    if not assessment:
        from app.models.membership import Membership as _Membership
        admin_membership = db.query(_Membership).filter(
            _Membership.user_id == current_user.id,
            _Membership.role.has(name="admin")
        ).first()
        if admin_membership:
            assessment = db.query(Assessment).filter(
                Assessment.id == assessment_uuid
            ).first()
            if assessment:
                member_membership = db.query(_Membership).filter(
                    _Membership.user_id == assessment.user_id,
                    _Membership.organization_id == admin_membership.organization_id
                ).first()
                if not member_membership:
                    assessment = None

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    if assessment.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment is not yet completed"
        )

    if assessment.instrument_type == "myimpact":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF download is only available for GPS assessments"
        )

    scoring_service = ScoringService(db)
    graded = scoring_service.grade_assessment(assessment)

    owner = db.query(User).filter(User.id == assessment.user_id).first()
    user_name = f"{owner.first_name or ''} {owner.last_name or ''}".strip() if owner else "Unknown"

    pdf_buffer = generate_pdf(
        graded=graded,
        user_name=user_name,
        completed_at=assessment.completed_at,
    )

    safe_name = user_name.replace(" ", "_") or "gps"
    filename = f"gps-results-{safe_name}.pdf"

    return StreamingResponse(
        iter([pdf_buffer.read()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{assessment_id}/continue", response_model=AssessmentFormData)
@limiter.limit(AUTHENTICATED_RATE)
async def continue_assessment(
    request: Request,
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Continue an in-progress assessment — returns questions + saved answers"""
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

    if assessment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment already completed"
        )

    instrument_type = assessment.instrument_type or "gps"

    # Get questions with eagerly loaded types
    questions = db.query(Question).filter(
        Question.instrument_type == instrument_type
    ).options(
        joinedload(Question.type),
        joinedload(Question.question_type),
    ).all()

    # Sort GPS questions in correct flow order
    if instrument_type == "gps":
        def gps_sort_key(q):
            type_name = q.type.name if q.type else ""
            qtype_name = q.question_type.type if q.question_type else ""
            passion = q.passion_type or ""
            if type_name == "Spiritual Gift" and qtype_name == "likert":
                return (0, q.order)
            elif type_name == "Spiritual Gift" and qtype_name == "multiple_choice":
                return (1, q.order)
            elif type_name == "Influencing Style" and qtype_name == "multiple_choice" and passion == "People":
                return (2, q.order)
            elif type_name == "Influencing Style" and qtype_name == "multiple_choice" and passion == "Cause":
                return (3, q.order)
            elif type_name == "Influencing Style" and qtype_name == "likert":
                return (4, q.order)
            elif type_name == "Story":
                return (5, q.order)
            else:
                return (6, q.order)
        questions = sorted(questions, key=gps_sort_key)
    else:
        questions = sorted(questions, key=lambda q: q.order)

    # Get saved answers
    saved_answers = db.query(Answer).filter(
        Answer.assessment_id == assessment_uuid
    ).all()

    answered_count = len(saved_answers)

    return AssessmentFormData(
        assessment_id=assessment.id,
        instrument_type=instrument_type,
        questions=[
            QuestionForAssessment(
                id=q.id,
                question=q.question,
                question_es=q.question_es,
                order=q.order,
                type_id=q.type_id,
                question_type_id=q.question_type_id,
                passion_type=q.passion_type,
                default_text=q.default_text,
                summary=q.summary,
                section=q.section,
                question_type_name=q.question_type.type if q.question_type else None,
                type_name=q.type.name if q.type else None,
            )
            for q in questions
        ],
        progress={
            "total_questions": len(questions),
            "answered": answered_count,
            "remaining": len(questions) - answered_count
        },
        saved_answers=saved_answers,
    )


@router.get("/my-assessments", response_model=List[AssessmentResponse])
@limiter.limit(AUTHENTICATED_RATE)
async def get_my_assessments(
    request: Request,
    instrument_type: Optional[str] = Query(None, description="Filter by instrument type: 'gps' or 'myimpact'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all assessments for current user"""
    query = db.query(Assessment).filter(
        Assessment.user_id == current_user.id
    )
    
    # Filter by instrument type if provided
    if instrument_type:
        if instrument_type not in ["gps", "myimpact"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid instrument_type. Must be 'gps' or 'myimpact'."
            )
        query = query.filter(Assessment.instrument_type == instrument_type)
    
    assessments = query.order_by(Assessment.created_at.desc()).all()
    return assessments


def build_myimpact_result_response(result: MyImpactResult) -> MyImpactResultResponse:
    """Build MyImpact result response with all details"""
    return MyImpactResultResponse(
        id=result.id,
        assessment_id=result.assessment_id,
        user_id=result.user_id,
        # Character scores
        character_score=round(result.character_score, 2) if result.character_score else None,
        c1_loving=result.c1_loving,
        c2_joyful=result.c2_joyful,
        c3_peaceful=result.c3_peaceful,
        c4_patient=result.c4_patient,
        c5_kind=result.c5_kind,
        c6_good=result.c6_good,
        c7_faithful=result.c7_faithful,
        c8_gentle=result.c8_gentle,
        c9_self_controlled=result.c9_self_controlled,
        # Calling scores
        calling_score=round(result.calling_score, 2) if result.calling_score else None,
        cl1_know_gifts=result.cl1_know_gifts,
        cl2_know_people=result.cl2_know_people,
        cl3_using_gifts=result.cl3_using_gifts,
        cl4_see_impact=result.cl4_see_impact,
        cl5_experience_joy=result.cl5_experience_joy,
        cl6_pray_regularly=result.cl6_pray_regularly,
        cl7_see_movement=result.cl7_see_movement,
        cl8_receive_support=result.cl8_receive_support,
        # Final score
        myimpact_score=round(result.myimpact_score, 2) if result.myimpact_score else None,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def build_result_with_details(db: Session, result: AssessmentResult) -> AssessmentResultWithDetails:
    """Build result response with full gift/passion details"""
    
    # Get gift details
    gifts = {}
    for i in range(1, 5):
        gift_id = getattr(result, f'gift_{i}_id')
        if gift_id:
            gift = db.query(GiftsPassion).filter(GiftsPassion.id == gift_id).first()
            if gift:
                gifts[i] = gift
    
    # Get passion details
    passions = {}
    for i in range(1, 4):
        passion_id = getattr(result, f'passion_{i}_id')
        if passion_id:
            passion = db.query(GiftsPassion).filter(GiftsPassion.id == passion_id).first()
            if passion:
                passions[i] = passion
    
    return AssessmentResultWithDetails(
        id=result.id,
        assessment_id=result.assessment_id,
        user_id=result.user_id,
        gift_1_id=result.gift_1_id,
        spiritual_gift_1_score=result.spiritual_gift_1_score,
        gift_1_name=gifts.get(1).name if 1 in gifts else None,
        gift_1_description=gifts.get(1).description if 1 in gifts else None,
        gift_2_id=result.gift_2_id,
        spiritual_gift_2_score=result.spiritual_gift_2_score,
        gift_2_name=gifts.get(2).name if 2 in gifts else None,
        gift_2_description=gifts.get(2).description if 2 in gifts else None,
        gift_3_id=result.gift_3_id,
        spiritual_gift_3_score=result.spiritual_gift_3_score,
        gift_3_name=gifts.get(3).name if 3 in gifts else None,
        gift_3_description=gifts.get(3).description if 3 in gifts else None,
        gift_4_id=result.gift_4_id,
        spiritual_gift_4_score=result.spiritual_gift_4_score,
        gift_4_name=gifts.get(4).name if 4 in gifts else None,
        gift_4_description=gifts.get(4).description if 4 in gifts else None,
        passion_1_id=result.passion_1_id,
        passion_1_score=result.passion_1_score,
        passion_1_name=passions.get(1).name if 1 in passions else None,
        passion_1_description=passions.get(1).description if 1 in passions else None,
        passion_2_id=result.passion_2_id,
        passion_2_score=result.passion_2_score,
        passion_2_name=passions.get(2).name if 2 in passions else None,
        passion_2_description=passions.get(2).description if 2 in passions else None,
        passion_3_id=result.passion_3_id,
        passion_3_score=result.passion_3_score,
        passion_3_name=passions.get(3).name if 3 in passions else None,
        passion_3_description=passions.get(3).description if 3 in passions else None,
        people=result.people,
        people_list=result.people.split(',') if result.people else [],
        cause=result.cause,
        cause_list=result.cause.split(',') if result.cause else [],
        abilities=result.abilities,
        abilities_list=result.abilities.split(',') if result.abilities else [],
        story_gift_answer=result.story_gift_answer,
        story_ability_answer=result.story_ability_answer,
        story_passion_answer=result.story_passion_answer,
        story_influencing_answer=result.story_influencing_answer,
        story_onechange_answer=result.story_onechange_answer,
        story_closestpeople_answer=result.story_closestpeople_answer,
        story_oneregret_answer=result.story_oneregret_answer,
        created_at=result.created_at,
        updated_at=result.updated_at
    )
