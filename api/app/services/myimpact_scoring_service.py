"""
MyImpact Assessment Scoring Service
Implements the scoring algorithm per the spec:
- Character Score = Average of 9 Character questions (1-10 scale)
- Calling Score = Average of 8 Calling questions (1-10 scale)
- MyImpact Score = Character Score × Calling Score (1-100)
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.myimpact_result import MyImpactResult


@dataclass
class CharacterScores:
    """Character section scores (Fruit of the Spirit)"""
    c1_loving: int
    c2_joyful: int
    c3_peaceful: int
    c4_patient: int
    c5_kind: int
    c6_good: int
    c7_faithful: int
    c8_gentle: int
    c9_self_controlled: int
    average: float


@dataclass
class CallingScores:
    """Calling section scores"""
    cl1_know_gifts: int
    cl2_know_people: int
    cl3_using_gifts: int
    cl4_see_impact: int
    cl5_experience_joy: int
    cl6_pray_regularly: int
    cl7_see_movement: int
    cl8_receive_support: int
    average: float


@dataclass
class MyImpactGradedResult:
    """Complete MyImpact graded results"""
    character: CharacterScores
    calling: CallingScores
    myimpact_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "character": {
                "loving": self.character.c1_loving,
                "joyful": self.character.c2_joyful,
                "peaceful": self.character.c3_peaceful,
                "patient": self.character.c4_patient,
                "kind": self.character.c5_kind,
                "good": self.character.c6_good,
                "faithful": self.character.c7_faithful,
                "gentle": self.character.c8_gentle,
                "self_controlled": self.character.c9_self_controlled,
                "average": round(self.character.average, 2),
            },
            "calling": {
                "know_gifts": self.calling.cl1_know_gifts,
                "know_people": self.calling.cl2_know_people,
                "using_gifts": self.calling.cl3_using_gifts,
                "see_impact": self.calling.cl4_see_impact,
                "experience_joy": self.calling.cl5_experience_joy,
                "pray_regularly": self.calling.cl6_pray_regularly,
                "see_movement": self.calling.cl7_see_movement,
                "receive_support": self.calling.cl8_receive_support,
                "average": round(self.calling.average, 2),
            },
            "myimpact_score": round(self.myimpact_score, 2),
        }


class MyImpactScoringService:
    """Service for grading MyImpact assessments"""
    
    # Question IDs for each section (based on sort order in myimpact_questions.csv)
    CHARACTER_QUESTION_ORDERS = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # Questions 1-9
    CALLING_QUESTION_ORDERS = [10, 11, 12, 13, 14, 15, 16, 17]  # Questions 10-17
    
    def __init__(self, db: Session):
        self.db = db
    
    def grade_assessment(self, assessment: Assessment) -> MyImpactGradedResult:
        """
        Grade a completed MyImpact assessment.
        
        Returns:
            MyImpactGradedResult with character, calling, and final MyImpact score
        """
        # Load answers if not already loaded
        if not assessment.answers:
            assessment = self.db.query(Assessment).filter(
                Assessment.id == assessment.id
            ).first()
        
        # Build answer lookup by question order
        answers_by_order = {}
        for answer in assessment.answers:
            if answer.question:
                answers_by_order[answer.question.order] = answer.numeric_value
        
        # Calculate Character Score (Questions 1-9)
        character_scores = []
        for order in self.CHARACTER_QUESTION_ORDERS:
            score = answers_by_order.get(order, 0)
            character_scores.append(score)
        
        character_average = sum(character_scores) / len(character_scores) if character_scores else 0
        
        character = CharacterScores(
            c1_loving=character_scores[0] if len(character_scores) > 0 else 0,
            c2_joyful=character_scores[1] if len(character_scores) > 1 else 0,
            c3_peaceful=character_scores[2] if len(character_scores) > 2 else 0,
            c4_patient=character_scores[3] if len(character_scores) > 3 else 0,
            c5_kind=character_scores[4] if len(character_scores) > 4 else 0,
            c6_good=character_scores[5] if len(character_scores) > 5 else 0,
            c7_faithful=character_scores[6] if len(character_scores) > 6 else 0,
            c8_gentle=character_scores[7] if len(character_scores) > 7 else 0,
            c9_self_controlled=character_scores[8] if len(character_scores) > 8 else 0,
            average=character_average,
        )
        
        # Calculate Calling Score (Questions 10-17)
        calling_scores = []
        for order in self.CALLING_QUESTION_ORDERS:
            score = answers_by_order.get(order, 0)
            calling_scores.append(score)
        
        calling_average = sum(calling_scores) / len(calling_scores) if calling_scores else 0
        
        calling = CallingScores(
            cl1_know_gifts=calling_scores[0] if len(calling_scores) > 0 else 0,
            cl2_know_people=calling_scores[1] if len(calling_scores) > 1 else 0,
            cl3_using_gifts=calling_scores[2] if len(calling_scores) > 2 else 0,
            cl4_see_impact=calling_scores[3] if len(calling_scores) > 3 else 0,
            cl5_experience_joy=calling_scores[4] if len(calling_scores) > 4 else 0,
            cl6_pray_regularly=calling_scores[5] if len(calling_scores) > 5 else 0,
            cl7_see_movement=calling_scores[6] if len(calling_scores) > 6 else 0,
            cl8_receive_support=calling_scores[7] if len(calling_scores) > 7 else 0,
            average=calling_average,
        )
        
        # Calculate Final MyImpact Score
        myimpact_score = character_average * calling_average
        
        return MyImpactGradedResult(
            character=character,
            calling=calling,
            myimpact_score=myimpact_score,
        )
    
    def create_result(self, assessment: Assessment) -> MyImpactResult:
        """
        Create and save MyImpactResult record from graded assessment.
        
        Args:
            assessment: Completed MyImpact assessment
            
        Returns:
            Saved MyImpactResult
        """
        graded = self.grade_assessment(assessment)
        
        result = MyImpactResult(
            assessment_id=assessment.id,
            user_id=assessment.user_id,
            # Character scores
            c1_loving=graded.character.c1_loving,
            c2_joyful=graded.character.c2_joyful,
            c3_peaceful=graded.character.c3_peaceful,
            c4_patient=graded.character.c4_patient,
            c5_kind=graded.character.c5_kind,
            c6_good=graded.character.c6_good,
            c7_faithful=graded.character.c7_faithful,
            c8_gentle=graded.character.c8_gentle,
            c9_self_controlled=graded.character.c9_self_controlled,
            character_score=graded.character.average,
            # Calling scores
            cl1_know_gifts=graded.calling.cl1_know_gifts,
            cl2_know_people=graded.calling.cl2_know_people,
            cl3_using_gifts=graded.calling.cl3_using_gifts,
            cl4_see_impact=graded.calling.cl4_see_impact,
            cl5_experience_joy=graded.calling.cl5_experience_joy,
            cl6_pray_regularly=graded.calling.cl6_pray_regularly,
            cl7_see_movement=graded.calling.cl7_see_movement,
            cl8_receive_support=graded.calling.cl8_receive_support,
            calling_score=graded.calling.average,
            # Final score
            myimpact_score=graded.myimpact_score,
        )
        
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        
        return result
    
    def validate_answers(self, assessment: Assessment) -> Dict[str, Any]:
        """
        Validate that all required MyImpact questions have been answered.
        
        Returns:
            Dict with is_valid flag, missing count, and list of missing questions
        """
        if not assessment.answers:
            assessment = self.db.query(Assessment).filter(
                Assessment.id == assessment.id
            ).first()
        
        answered_orders = set()
        for answer in assessment.answers:
            if answer.question and answer.numeric_value is not None:
                answered_orders.add(answer.question.order)
        
        required_orders = set(self.CHARACTER_QUESTION_ORDERS + self.CALLING_QUESTION_ORDERS)
        missing_orders = required_orders - answered_orders
        
        missing_questions = []
        if missing_orders:
            for order in sorted(missing_orders):
                section = "Character" if order in self.CHARACTER_QUESTION_ORDERS else "Calling"
                missing_questions.append({
                    "order": order,
                    "section": section,
                })
        
        return {
            "is_valid": len(missing_orders) == 0,
            "missing_count": len(missing_orders),
            "missing_questions": missing_questions,
            "answered_count": len(answered_orders),
            "total_required": len(required_orders),
        }
