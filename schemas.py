from pydantic import BaseModel
from typing import List, Optional


class SurveyFormCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SurveyFormUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class SurveyQuestionCreate(BaseModel):
    text: str
    type: str  # e.g., "multiple_choice"
    options: Optional[List[str]] = None

class SurveyQuestionUpdate(BaseModel):
    text: Optional[str] = None
    is_active: Optional[bool] = None

class QuestionsReorder(BaseModel):
    question_ids: List[int]

# Updated schemas.py


class SurveyQuestionCreate(BaseModel):
    question_text: Optional[str] = None
    text: Optional[str] = None
    dimension: str = "General"
    question_type: Optional[str] = None
    type: Optional[str] = None
    order_index: int = 0
    options: Optional[List[str]] = []
    is_required: bool = True