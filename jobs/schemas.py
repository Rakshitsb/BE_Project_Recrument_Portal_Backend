from datetime import datetime
from typing import Any, Optional
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
    jd_parsed: Optional[dict[str, Any]] = None
    raw_jd_text: Optional[str] = None

    model_config = {"extra": "allow"}


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
    jd_parsed: Optional[dict[str, Any]] = None
    raw_jd_text: Optional[str] = None

    model_config = {"extra": "allow"}


class JobResponse(JobCreate):
    id: str
    hr_id: str
    created_at: datetime
    company_name: str | None = None
    industry: str | None = None
    company_size: str | None = None

    model_config = {"extra": "allow", "from_attributes": True}
