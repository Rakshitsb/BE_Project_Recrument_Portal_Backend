from pydantic import BaseModel, Field


class JDParseRequest(BaseModel):
    jd_text: str = Field(..., min_length=50)


class ParsedJD(BaseModel):
    title: str
    summary: str
    responsibilities: list[str]
    required_skills: list[str]
    nice_to_have_skills: list[str]
    experience_required: str
    education_required: str
    job_type: str
    location: str
    salary_range: str
    company_culture: str
    keywords: list[str]


class JDParseResponse(BaseModel):
    parsed_jd: ParsedJD
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
