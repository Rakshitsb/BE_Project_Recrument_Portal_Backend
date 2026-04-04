from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: list[str]
    location: str
    job_type: str
    experience_required: float
    salary_range: str | None = None
    cover_letter_required: bool = False
    is_active: bool = True


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list[str]] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_required: Optional[float] = None
    salary_range: Optional[str] = None
    cover_letter_required: Optional[bool] = None
    is_active: Optional[bool] = None


class JobResponse(JobCreate):
    id: str
    hr_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
