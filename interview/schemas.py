from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    application_id: str
    interviewer_id: str
    name: str
    objective: str
    question_count: int = Field(ge=1, le=20)
    time_duration: str
    context: str = ""


class InterviewUpdate(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    time_duration: Optional[str] = None
    is_active: Optional[bool] = None
    regenerate_questions: bool = False
    context: str = ""


class QuestionOut(BaseModel):
    id: str
    question: str
    follow_up_count: int


class InterviewResponse(BaseModel):
    id: str
    interview_token: str
    application_id: str
    job_id: str
    hr_id: str
    candidate_id: str
    interviewer_id: str
    name: str
    objective: str
    context: str = ""
    description: str
    questions: list[QuestionOut]
    question_count: int
    time_duration: str
    is_active: bool
    is_archived: bool
    response_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterviewSummary(BaseModel):
    id: str
    interview_token: str
    application_id: str
    job_id: str
    hr_id: str
    candidate_id: str
    name: str
    objective: str
<<<<<<< HEAD
    context: str = ""
=======
>>>>>>> 6cda33488b4bb35745a77d86bee4a45713de2e6c
    description: str
    question_count: int
    time_duration: str
    is_active: bool
    response_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
