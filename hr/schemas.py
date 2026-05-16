from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HRProfileCreate(BaseModel):
    full_name: str
    phone: str
    designation: str
    company_name: str
    company_website: str | None = None
    company_location: str
    industry: str
    company_size: str
    avatar_url: str | None = None
    avatar_public_id: str | None = None
    profile_image: dict | None = None


class HRProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_location: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_public_id: Optional[str] = None
    profile_image: Optional[dict] = None


class HRProfileResponse(HRProfileCreate):
    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HRDashboardStats(BaseModel):
    total_jobs_posted: int = 0
    active_jobs: int = 0
    total_applicants: int = 0
    positions_filled: int = 0


class HRDashboardJob(BaseModel):
    id: str
    title: str
    is_active: bool = True
    applicants: int = 0
    created_at: datetime


class HRDashboardApplication(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    job_title: str | None = None
    candidate_name: str | None = None
    candidate_email: str | None = None
    candidate_avatar_url: str | None = None
    status: str
    created_at: datetime


class HRDashboardResponse(BaseModel):
    stats: HRDashboardStats
    jobs: list[HRDashboardJob] = Field(default_factory=list)
    recent_applicants: list[HRDashboardApplication] = Field(default_factory=list)
