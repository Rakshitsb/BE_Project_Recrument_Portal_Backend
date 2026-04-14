from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InterviewerCreate(BaseModel):
    agent_id: str
    name: str
    description: str
    image: str
    audio: Optional[str] = None
    empathy: int = Field(ge=1, le=10)
    exploration: int = Field(ge=1, le=10)
    rapport: int = Field(ge=1, le=10)
    speed: int = Field(ge=1, le=10)


class InterviewerResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    description: str
    image: str
    audio: Optional[str] = None
    empathy: int
    exploration: int
    rapport: int
    speed: int
    created_at: datetime

    model_config = {"from_attributes": True}
