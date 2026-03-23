from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user, require_admin
from app.models.user import User
from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.question import Question
from app.models.assessment_result import AssessmentResult
from app.models.gifts_passion import GiftsPassion
from app.services.scoring_service import ScoringService
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentResponse,
    AssessmentWithAnswers,
    AssessmentSubmit,
    AssessmentResultWithDetails,
    QuestionForAssessment,
    AssessmentFormData,
    GradedAssessmentResponse,
)

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post("/start", response_model=AssessmentFormData, status_code=status.HTTP_201_CREATED)
async def start_assessment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Start a new assessment and return the form data"""
    # Create new assessment
    assessment = Assessment(
        user_id=current_user.id,
        status="in_progress"
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    # Get all questions
    questions = db.query(Question).order_by(Question.order).all()
    
    return AssessmentFormData(
        assessment_id=assessment.id,
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
async def save_progress(
    assessment_id: str,
    submit_data: AssessmentSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Save assessment progress (answers) without completing"""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
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
            Answer.assessment_id == assessment_id,
            Answer.question_id == answer_data.question_id
        ).first()
        
        if existing:
            # Update existing
            existing.multiple_choice_answer = answer_data.multiple_choice_answer
            existing.numeric_value = answer_data.numeric_value
            existing.text_value = answer_data.text_value
        else:
            # Create new
            answer = Answer(
                assessment_id=assessment_id,
                question_id=answer_data.question_id,
                user_id=current_user.id,
                multiple_choice_answer=answer_data.multiple_choice_answer,
                numeric_value=answer_data.numeric_value,
                text_value=answer_data.text_value
            )
            db.add(answer)
    
    db.commit()
    db.refresh(assessment)
    
    return assessment


@router.post("/{assessment_id}/submit", response_model=AssessmentResultWithDetails)
async def submit_assessment(
    assessment_id: str,
    submit_data: AssessmentSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit assessment and get results"""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
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
            Answer.assessment_id == assessment_id,
            Answer.question_id == answer_data.question_id
        ).first()
        
        if existing:
            existing.multiple_choice_answer = answer_data.multiple_choice_answer
            existing.numeric_value = answer_data.numeric_value
            existing.text_value = answer_data.text_value
        else:
            answer = Answer(
                assessment_id=assessment_id,
                question_id=answer_data.question_id,
                user_id=current_user.id,
                multiple_choice_answer=answer_data.multiple_choice_answer,
                numeric_value=answer_data.numeric_value,
                text_value=answer_data.text_value
            )
            db.add(answer)
    
    # Mark as completed
    assessment.status = "completed"
    assessment.completed_at = datetime.utcnow()
    db.commit()
    
    # Grade the assessment
    scoring_service = ScoringService(db)
    
    # Validate all questions answered
    validation = scoring_service.validate_answers(assessment)
    if not validation['is_valid']:
        # Allow submission but log missing
        print(f"Assessment {assessment_id} submitted with {validation['missing_count']} missing answers")
    
    # Create results
    result = scoring_service.create_assessment_result(assessment)
    
    # Build detailed response
    return build_result_with_details(db, result)


@router.get("/{assessment_id}/results", response_model=AssessmentResultWithDetails)
async def get_assessment_results(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get results for a completed assessment"""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
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
    
    result = db.query(AssessmentResult).filter(
        AssessmentResult.assessment_id == assessment_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found"
        )
    
    return build_result_with_details(db, result)


@router.get("/{assessment_id}/grade", response_model=GradedAssessmentResponse)
async def grade_assessment_preview(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Preview grade calculation without saving results"""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
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


@router.get("/my-assessments", response_model=List[AssessmentResponse])
async def get_my_assessments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all assessments for current user"""
    assessments = db.query(Assessment).filter(
        Assessment.user_id == current_user.id
    ).order_by(Assessment.created_at.desc()).all()
    
    return assessments


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
            passion = db.query(GiftsPassion).filter(GiftsPassions.id == passion_id).first()
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
