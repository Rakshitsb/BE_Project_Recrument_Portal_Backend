from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class HRProfileCreate(BaseModel):
    full_name: str
    phone: str
    designation: str
    company_name: str
    company_website: str | None = None
    company_location: str
    industry: str
    company_size: str


class HRProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_location: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None


class HRProfileResponse(HRProfileCreate):
    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
