from typing import Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Question(BaseModel):
    question: str


class InterviewStatus(str, Enum):
    pending = "pending"
    active = "active"
    completed = "completed"
    expired = "expired"


class InterviewCreate(BaseModel):
    application_id: str
    job_id: str
    name: str
    objective: str
    questions: list[Question]
    interviewer_id: str
    duration_mins: int = 15


class InterviewUpdate(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    questions: Optional[list[Question]] = None
    interviewer_id: Optional[str] = None
    duration_mins: Optional[int] = None
    status: Optional[InterviewStatus] = None


class InterviewResponse(BaseModel):
    id: str
    application_id: str
    job_id: str
    hr_id: str
    candidate_id: str
    name: str
    objective: str
    questions: list[Question]
    interviewer_id: str
    duration_mins: int
    status: InterviewStatus
    interview_url: str
    readable_slug: str
    insights: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateQuestionsRequest(BaseModel):
    job_title: str
    objective: str
    number: int = 5
    context: str = ""


class AnalyticsResponse(BaseModel):
    overall_score: float
    overall_feedback: str
    communication: dict
    question_summaries: list[dict]
    soft_skill_summary: str
    main_interview_questions: list[str] = []


class ResponseRecord(BaseModel):
    id: str
    interview_id: str
    candidate_id: str
    call_id: str
    is_ended: bool = False
    is_analysed: bool = False
    duration: Optional[int] = None
    details: Optional[dict] = None
    analytics: Optional[AnalyticsResponse] = None
    created_at: datetime

    model_config = {"from_attributes": True}
