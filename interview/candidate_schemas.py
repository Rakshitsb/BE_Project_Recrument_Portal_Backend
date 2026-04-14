"""Candidate-facing interview schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CandidateInterviewerView(BaseModel):
    id: str
    name: str
    description: str
    image: str
    audio: Optional[str] = None
    empathy: int
    exploration: int
    rapport: int
    speed: int


class CandidateInterviewView(BaseModel):
    id: str
    name: str
    description: str
    interviewer: CandidateInterviewerView
    time_duration: str
    question_count: int
    is_active: bool
    created_at: datetime


class CandidateInterviewSummary(BaseModel):
    id: str
    name: str
    description: str
    time_duration: str
    question_count: int
    is_active: bool
    created_at: datetime
    interview_token: str


class RegisterCallRequest(BaseModel):
    candidate_name: str
    candidate_email: str


class RegisterCallResponse(BaseModel):
    call_id: str
    access_token: str
    interview_id: str
