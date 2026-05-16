from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class CandidateProfileCreate(BaseModel):
    full_name: str
    phone: str
    location: Optional[str] = ""
    skills: list[str] = []
    experience_years: float = 0
    # education can be a string (legacy) or a structured array
    education: Any = None
    # structured arrays from AI resume parsing
    experience: Optional[list[dict]] = None
    projects: Optional[list[dict]] = None
    resume_url: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_public_id: Optional[str] = None
    profile_image: Optional[dict] = None
    bio: Optional[str] = None

    # Allow any extra fields (e.g. gender, dob, certifications) to pass
    # through without being validated or stripped.
    model_config = {"extra": "allow"}


class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[list[str]] = None
    experience_years: Optional[float] = None
    education: Any = None
    experience: Optional[list[dict]] = None
    projects: Optional[list[dict]] = None
    resume_url: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_public_id: Optional[str] = None
    profile_image: Optional[dict] = None
    bio: Optional[str] = None

    model_config = {"extra": "allow"}


class CandidateProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: list[str] = []
    experience_years: float = 0
    education: Any = None
    experience: Optional[list[dict]] = None
    projects: Optional[list[dict]] = None
    resume_url: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_public_id: Optional[str] = None
    profile_image: Optional[dict] = None
    bio: Optional[str] = None
    created_at: datetime

    # Allow extra stored fields (gender, dob, etc.) to be returned as-is
    model_config = {"extra": "allow", "from_attributes": True}
