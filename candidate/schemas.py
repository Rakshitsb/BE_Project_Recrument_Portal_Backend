from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CandidateProfileCreate(BaseModel):
    full_name: str
    phone: str
    location: str
    skills: list[str]
    experience_years: float
    education: str
    resume_url: str | None = None
    bio: str | None = None


class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[list[str]] = None
    experience_years: Optional[float] = None
    education: Optional[str] = None
    resume_url: Optional[str] = None
    bio: Optional[str] = None


class CandidateProfileResponse(CandidateProfileCreate):
    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
