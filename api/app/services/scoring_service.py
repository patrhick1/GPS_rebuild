"""
GPS Assessment Scoring Service
Ports the Laravel scoring algorithm to Python
"""
import uuid as uuid_mod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from collections import defaultdict

from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.gifts_passion import GiftsPassion
from app.models.question import Question
from app.models.type import Type
from app.models.assessment_result import AssessmentResult


@dataclass
class GiftPassionResult:
    """Result for a single gift or passion"""
    id: str
    name: str
    short_code: str
    description: str
    points: int


@dataclass
class StoryKeyPair:
    """Story question and answer pair"""
    question: str
    answer: str
    question_es: Optional[str] = None


@dataclass
class GradedAssessment:
    """Complete graded assessment results"""
    gifts: List[GiftPassionResult] = field(default_factory=list)
    top_gifts: List[GiftPassionResult] = field(default_factory=list)
    passions: List[GiftPassionResult] = field(default_factory=list)
    top_passions: List[GiftPassionResult] = field(default_factory=list)
    abilities: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    causes: List[str] = field(default_factory=list)
    stories: List[StoryKeyPair] = field(default_factory=list)


class ScoringService:
    """Service for grading GPS assessments"""
    
    # Special question IDs from Laravel
    ABILITY_QUESTION_ID = 166
    PEOPLE_QUESTION_ID = 157
    CAUSE_QUESTION_ID = 158
    
    def __init__(self, db: Session):
        self.db = db
    
    def grade_assessment(self, assessment: Assessment) -> GradedAssessment:
        """
        Grade a completed assessment and return results.
        This is the main entry point - ports AssessmentUtility::gradeAssessment()
        """
        # Load all answers
        if not assessment.answers:
            assessment = self.db.query(Assessment).filter(
                Assessment.id == assessment.id
            ).first()
        
        # Get all gifts and passions
        gifts_passions = self.db.query(GiftsPassion).all()
        
        # Filter by type
        gifts = [gp for gp in gifts_passions if gp.type.name == "Spiritual Gift"]
        passions = [gp for gp in gifts_passions if gp.type.name == "Influencing Style"]
        
        # Calculate scores
        gift_results = self._calculate_gifts(assessment, gifts)
        passion_results = self._calculate_passions(assessment, passions)
        
        # Build graded assessment
        graded = GradedAssessment()
        graded.gifts = gift_results
        graded.passions = passion_results
        
        # Get top results (handles ties)
        graded.top_gifts = self._get_top_results(gift_results, 4, limit_top=2)
        graded.top_passions = self._get_top_results(passion_results, 3, limit_top=2)
        
        # Get special answers (convert order numbers to UUIDs)
        order_map = self._build_order_to_uuid_map()
        graded.abilities = self._get_checkbox_answers(assessment, order_map.get(self.ABILITY_QUESTION_ID))
        graded.people = self._get_checkbox_answers(assessment, order_map.get(self.PEOPLE_QUESTION_ID))
        graded.causes = self._get_checkbox_answers(assessment, order_map.get(self.CAUSE_QUESTION_ID))
        graded.stories = self._get_stories(assessment)
        
        return graded
    
    def _build_order_to_uuid_map(self) -> dict:
        """Build a mapping from question order number to question UUID"""
        questions = self.db.query(Question).all()
        return {q.order: q.id for q in questions}

    def _calculate_gifts(self, assessment: Assessment, gifts: List[GiftsPassion]) -> List[GiftPassionResult]:
        """Calculate scores for all spiritual gifts"""
        results = []
        order_map = self._build_order_to_uuid_map()

        for gift in gifts:
            # Parse question order numbers from comma-separated string
            question_orders = [int(q.strip()) for q in gift.questions.split(',') if q.strip()]
            # Convert order numbers to UUIDs
            question_uuids = [order_map[o] for o in question_orders if o in order_map]

            # Sum the scores
            score = self._sum_answer_values(assessment, question_uuids)
            
            results.append(GiftPassionResult(
                id=str(gift.id),
                name=gift.name,
                short_code=gift.short_code,
                description=gift.description,
                points=score
            ))
        
        # Sort by points descending
        results.sort(key=lambda x: x.points, reverse=True)
        return results
    
    def _calculate_passions(self, assessment: Assessment, passions: List[GiftsPassion]) -> List[GiftPassionResult]:
        """Calculate scores for all influencing styles"""
        results = []
        order_map = self._build_order_to_uuid_map()

        # Get offset for passion questions (Laravel uses this)
        first_passion_question = self.db.query(Question).join(Type).filter(
            Type.name == "Influencing Style"
        ).order_by(Question.order).first()

        offset = 0
        if first_passion_question:
            # Laravel calculates offset based on question ID difference
            offset = first_passion_question.order - 1

        for passion in passions:
            # Parse question order numbers
            question_orders = [int(q.strip()) for q in passion.questions.split(',') if q.strip()]

            # Apply offset (Laravel does this for passions)
            if offset > 0:
                question_orders = [q + offset for q in question_orders]

            # Convert order numbers to UUIDs
            question_uuids = [order_map[o] for o in question_orders if o in order_map]

            # Sum the scores
            score = self._sum_answer_values(assessment, question_uuids)
            
            results.append(GiftPassionResult(
                id=str(passion.id),
                name=passion.name,
                short_code=passion.short_code,
                description=passion.description,
                points=score
            ))
        
        # Sort by points descending
        results.sort(key=lambda x: x.points, reverse=True)
        return results
    
    def _sum_answer_values(self, assessment: Assessment, question_ids: List) -> int:
        """Sum numeric values for given question IDs"""
        total = 0
        
        for answer in assessment.answers:
            if answer.question_id in question_ids and answer.numeric_value:
                total += answer.numeric_value
        
        return total
    
    def _get_top_results(self, results: List[GiftPassionResult], hard_limit: int, limit_top: int) -> List[GiftPassionResult]:
        """
        Get top results with tie handling.
        
        Args:
            results: Sorted list of results (descending by points)
            hard_limit: Maximum number to return (4 for gifts, 3 for passions)
            limit_top: Minimum number to always include (2 for both)
        """
        if not results:
            return []
        
        top_results = []
        
        for i, result in enumerate(results):
            if i < (limit_top - 1):
                # Always include up to limit_top-1
                top_results.append(result)
            else:
                # Check for ties
                last_included = top_results[-1] if top_results else None
                if last_included and result.points == last_included.points:
                    # Include tied scores
                    top_results.append(result)
                elif i < hard_limit:
                    # Include if under hard limit
                    top_results.append(result)
                else:
                    # Stop when we hit hard limit and no tie
                    break
            
            if len(top_results) >= hard_limit:
                break
        
        return top_results
    
    def _get_checkbox_answers(self, assessment: Assessment, question_id: Optional[Any]) -> List[str]:
        """Get checkbox/multiple choice answers for a question"""
        if question_id is None:
            return []

        answers = []

        for answer in assessment.answers:
            if answer.question_id == question_id:
                value = answer.multiple_choice_answer
                if value:
                    # Handle "Other" responses with text
                    if value.lower() == 'other' and answer.text_value:
                        value = f"{value}: {answer.text_value}"
                    answers.append(value)
        
        return answers
    
    def _get_stories(self, assessment: Assessment) -> List[StoryKeyPair]:
        """Get story/free text question answers"""
        stories = []
        
        # Get all story questions (type_id = 3)
        story_questions = self.db.query(Question).join(Type).filter(
            Type.name == "Story"
        ).all()
        
        for question in story_questions:
            # Find answer for this question
            answer = next(
                (a for a in assessment.answers if a.question_id == question.id),
                None
            )
            
            if answer and answer.text_value:
                stories.append(StoryKeyPair(
                    question=question.question,
                    answer=answer.text_value,
                    question_es=question.question_es
                ))
        
        return stories
    
    def create_assessment_result(self, assessment: Assessment) -> AssessmentResult:
        """
        Create and save AssessmentResult record from graded assessment.
        Ports AssessmentResultUtility::createResult()
        """
        graded = self.grade_assessment(assessment)
        
        # Helper to convert string IDs back to UUID objects for the ORM
        def _to_uuid(val):
            if val is None:
                return None
            return uuid_mod.UUID(val) if isinstance(val, str) else val

        # Build result data
        result_data = {
            'assessment_id': assessment.id,
            'user_id': assessment.user_id,
            'gift_1_id': _to_uuid(graded.top_gifts[0].id) if len(graded.top_gifts) > 0 else None,
            'spiritual_gift_1_score': graded.top_gifts[0].points if len(graded.top_gifts) > 0 else None,
            'gift_2_id': _to_uuid(graded.top_gifts[1].id) if len(graded.top_gifts) > 1 else None,
            'spiritual_gift_2_score': graded.top_gifts[1].points if len(graded.top_gifts) > 1 else None,
            'gift_3_id': _to_uuid(graded.top_gifts[2].id) if len(graded.top_gifts) > 2 else None,
            'spiritual_gift_3_score': graded.top_gifts[2].points if len(graded.top_gifts) > 2 else None,
            'gift_4_id': _to_uuid(graded.top_gifts[3].id) if len(graded.top_gifts) > 3 else None,
            'spiritual_gift_4_score': graded.top_gifts[3].points if len(graded.top_gifts) > 3 else None,
            'passion_1_id': _to_uuid(graded.top_passions[0].id) if len(graded.top_passions) > 0 else None,
            'passion_1_score': graded.top_passions[0].points if len(graded.top_passions) > 0 else None,
            'passion_2_id': _to_uuid(graded.top_passions[1].id) if len(graded.top_passions) > 1 else None,
            'passion_2_score': graded.top_passions[1].points if len(graded.top_passions) > 1 else None,
            'passion_3_id': _to_uuid(graded.top_passions[2].id) if len(graded.top_passions) > 2 else None,
            'passion_3_score': graded.top_passions[2].points if len(graded.top_passions) > 2 else None,
            'people': ','.join(graded.people),
            'cause': ','.join(graded.causes),
            'abilities': ','.join(graded.abilities),
        }
        
        # Add story answers
        story_fields = [
            'story_gift_answer',
            'story_ability_answer',
            'story_passion_answer',
            'story_influencing_answer',
            'story_onechange_answer',
            'story_closestpeople_answer',
            'story_oneregret_answer',
        ]
        
        for i, story in enumerate(graded.stories):
            if i < len(story_fields):
                result_data[story_fields[i]] = story.answer
        
        # Create and save result
        result = AssessmentResult(**result_data)
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        
        return result
    
    def validate_answers(self, assessment: Assessment) -> Dict[str, Any]:
        """
        Validate that all required questions have been answered.
        Returns dict with is_valid flag and list of missing questions.
        """
        # Get all required questions
        questions = self.db.query(Question).all()
        
        answered_question_ids = {a.question_id for a in assessment.answers}
        
        missing = []
        for question in questions:
            if question.id not in answered_question_ids:
                missing.append({
                    'id': question.id,
                    'question': question.question
                })
        
        return {
            'is_valid': len(missing) == 0,
            'missing_count': len(missing),
            'missing_questions': missing
        }
