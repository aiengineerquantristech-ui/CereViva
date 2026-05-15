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