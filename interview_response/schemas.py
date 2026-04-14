from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyticsOut(BaseModel):
    overallScore: float | None = None
    overallFeedback: str | None = None
    communication: dict | None = None
    questionSummaries: list[dict] | None = None
    softSkillSummary: str | None = None


class InterviewResponseOut(BaseModel):
    id: str; interview_id: str; candidate_id: str; call_id: str
    name: str | None = None; email: str | None = None; duration: int | None = None
    analytics: AnalyticsOut | None = None; candidate_status: str
    is_analysed: bool; is_ended: bool; is_viewed: bool; tab_switch_count: int
    created_at: datetime; updated_at: datetime; model_config = ConfigDict(from_attributes=True)


class InterviewResponseSummary(BaseModel):
    id: str; interview_id: str; candidate_id: str; call_id: str
    name: str | None = None; email: str | None = None; duration: int | None = None
    candidate_status: str; is_analysed: bool; is_ended: bool; is_viewed: bool
    tab_switch_count: int; created_at: datetime


class CandidateResponseOut(BaseModel):
    id: str; interview_id: str; call_id: str; name: str | None = None
    duration: int | None = None; analytics: AnalyticsOut | None = None
    is_analysed: bool; is_ended: bool; created_at: datetime


class ResponseStatusUpdate(BaseModel):
    candidate_status: str

    @field_validator("candidate_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "selected", "rejected"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class TabSwitchUpdate(BaseModel):
    count: int = Field(ge=0)
