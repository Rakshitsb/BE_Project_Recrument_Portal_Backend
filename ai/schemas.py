from typing import Any

from pydantic import BaseModel


class JDParseResponse(BaseModel):
    parsed_jd: dict[str, Any]
    raw_text: str
    model_used: str


# ---------------------------------------------------------------------------
# Skill matcher schemas (added in Prompt 8)
# ---------------------------------------------------------------------------


class MatchJobRequest(BaseModel):
    job_id: str  # MongoDB ObjectId as string


class MatchJobResponse(BaseModel):
    job_id: str
    job_title: str
    score: float
    matched_skills: list[str]
    missing_skills: list[str]
    bonus_skills: list[str]
    experience_gap: float
    scoring_method: str
    confidence: str
