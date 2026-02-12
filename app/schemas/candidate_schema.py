from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class Education(BaseModel):
    degree: str
    institution: str
    year: str

class Experience(BaseModel):
    company: str
    role: str
    duration: str
    description: str

class Project(BaseModel):
    name: str = Field(default="")
    description: str = Field(default="")

class ResumeData(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    skills: List[str] = []
    education: List[Education] = []
    experience: List[Experience] = []
    projects: List[Project] = []

class CreateProfileRequest(ResumeData):
    resume_text: Optional[str] = ""

class CandidateProfile(ResumeData):
    id: str = Field(..., alias="_id")
    resume_text: str
    resume_embedding: List[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
