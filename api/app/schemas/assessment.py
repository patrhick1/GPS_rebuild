from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid


# Answer schemas
class AnswerBase(BaseModel):
    question_id: uuid.UUID
    multiple_choice_answer: Optional[str] = None
    numeric_value: Optional[int] = None
    text_value: Optional[str] = None


class AnswerCreate(AnswerBase):
    pass


class AnswerResponse(AnswerBase):
    id: uuid.UUID
    assessment_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Assessment schemas
class AssessmentBase(BaseModel):
    pass


class AssessmentCreate(BaseModel):
    pass


class AssessmentUpdate(BaseModel):
    status: Optional[str] = None  # in_progress, completed, abandoned


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssessmentWithAnswers(AssessmentResponse):
    answers: List[AnswerResponse] = []


# Submit assessment
class AssessmentSubmit(BaseModel):
    answers: List[AnswerCreate]


# Gift/Passion result
class GiftPassionResult(BaseModel):
    id: str
    name: str
    short_code: str
    description: str
    points: int


# Story result
class StoryResult(BaseModel):
    question: str
    answer: str
    question_es: Optional[str] = None


# Graded assessment response
class GradedAssessmentResponse(BaseModel):
    gifts: List[GiftPassionResult]
    top_gifts: List[GiftPassionResult]
    passions: List[GiftPassionResult]
    top_passions: List[GiftPassionResult]
    abilities: List[str]
    people: List[str]
    causes: List[str]
    stories: List[StoryResult]


# Assessment result schemas
class AssessmentResultBase(BaseModel):
    pass


class AssessmentResultResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    
    # Top gifts
    gift_1_id: Optional[uuid.UUID] = None
    spiritual_gift_1_score: Optional[int] = None
    gift_2_id: Optional[uuid.UUID] = None
    spiritual_gift_2_score: Optional[int] = None
    gift_3_id: Optional[uuid.UUID] = None
    spiritual_gift_3_score: Optional[int] = None
    gift_4_id: Optional[uuid.UUID] = None
    spiritual_gift_4_score: Optional[int] = None
    
    # Top passions
    passion_1_id: Optional[uuid.UUID] = None
    passion_1_score: Optional[int] = None
    passion_2_id: Optional[uuid.UUID] = None
    passion_2_score: Optional[int] = None
    passion_3_id: Optional[uuid.UUID] = None
    passion_3_score: Optional[int] = None
    
    # Selections
    people: Optional[str] = None
    cause: Optional[str] = None
    abilities: Optional[str] = None
    
    # Story answers
    story_gift_answer: Optional[str] = None
    story_ability_answer: Optional[str] = None
    story_passion_answer: Optional[str] = None
    story_influencing_answer: Optional[str] = None
    story_onechange_answer: Optional[str] = None
    story_closestpeople_answer: Optional[str] = None
    story_oneregret_answer: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssessmentResultWithDetails(AssessmentResultResponse):
    """Result with full gift/passion details"""
    gift_1_name: Optional[str] = None
    gift_1_description: Optional[str] = None
    gift_2_name: Optional[str] = None
    gift_2_description: Optional[str] = None
    gift_3_name: Optional[str] = None
    gift_3_description: Optional[str] = None
    gift_4_name: Optional[str] = None
    gift_4_description: Optional[str] = None
    
    passion_1_name: Optional[str] = None
    passion_1_description: Optional[str] = None
    passion_2_name: Optional[str] = None
    passion_2_description: Optional[str] = None
    passion_3_name: Optional[str] = None
    passion_3_description: Optional[str] = None
    
    people_list: List[str] = []
    cause_list: List[str] = []
    abilities_list: List[str] = []


# Question schemas for assessment form
class QuestionForAssessment(BaseModel):
    id: uuid.UUID
    question: str
    question_es: Optional[str] = None
    order: int
    type_id: uuid.UUID
    question_type_id: uuid.UUID
    passion_type: Optional[str] = None
    default_text: Optional[str] = None
    summary: Optional[str] = None


class AssessmentFormData(BaseModel):
    assessment_id: uuid.UUID
    questions: List[QuestionForAssessment]
    progress: Dict[str, Any]
