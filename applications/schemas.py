from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class ApplicationStatus(str, Enum):
    applied       = "applied"
    under_review  = "under_review"
    shortlisted   = "shortlisted"
    interview     = "interview"
    selected      = "selected"
    rejected      = "rejected"


class ApplicationCreate(BaseModel):
    job_id: str
    cover_letter: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    job_title: str | None = None
    company_name: str | None = None
    location: str | None = None
    salary_range: str | None = None
    cover_letter: str | None = None
    status: ApplicationStatus = ApplicationStatus.applied
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
