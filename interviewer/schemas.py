from pydantic import BaseModel


class InterviewerCreate(BaseModel):
    agent_id: str
    name: str
    rapport: int
    exploration: int
    empathy: int
    speed: int
    image: str
    audio: str
    description: str
    voice_id: str


class InterviewerResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    rapport: int
    exploration: int
    empathy: int
    speed: int
    image: str
    audio: str
    description: str

    model_config = {"from_attributes": True}
