from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class JobCreate(BaseModel):
    title: str
    description: str
    requiredSkills: List[str]


class JobResponse(BaseModel):
    id: str = Field(..., alias="_id")
    title: str
    description: str
    requiredSkills: List[str]
    createdBy: str
    createdAt: datetime
    isActive: bool

    class Config:
        populate_by_name = True
