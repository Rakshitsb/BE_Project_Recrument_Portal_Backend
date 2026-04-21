import json
import re

from fastapi import HTTPException, status
from groq import AsyncGroq

from ai.schemas import ParsedJD
from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

JD_PARSER_PROMPT = """
You are an expert job description parser.

Extract and return ONLY valid JSON with this exact shape:
{
  "title": "string",
  "summary": "string",
  "responsibilities": ["string"],
  "required_skills": ["string"],
  "nice_to_have_skills": ["string"],
  "experience_required": "string",
  "education_required": "string",
  "job_type": "string",
  "location": "string",
  "salary_range": "string",
  "company_culture": "string",
  "keywords": ["string"]
}

Rules:
- No preamble, no markdown, no backticks, no explanation
- If a field is not found, use empty string or empty list
- Keywords should help semantic job matching and be max 20 items
"""


async def parse_jd_with_groq(jd_text: str) -> ParsedJD:
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": JD_PARSER_PROMPT},
                {"role": "user", "content": jd_text},
            ],
            temperature=0.2,
        )

        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        parsed = json.loads(raw)
        if isinstance(parsed.get("keywords"), list):
            parsed["keywords"] = parsed["keywords"][:20]
        return ParsedJD(**parsed)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Model returned invalid JSON",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JD parsing failed: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Skill matcher helper (added in Prompt 8)
# ---------------------------------------------------------------------------


async def get_match_result(db, candidate_id: str, job_id: str) -> dict:
    """Fetch candidate + job from MongoDB and score them with the skill matcher.

    Args:
        db:           Motor async database instance.
        candidate_id: The authenticated candidate's user_id (string).
        job_id:       The job's MongoDB ObjectId as a string.

    Raises:
        HTTPException 404: Candidate profile or job not found.
        HTTPException 400: Invalid job_id format.

    Returns:
        MatchJobResponse-compatible dict.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    from ai_services.skill_matcher import match_candidate_to_job
    from db.collections import CANDIDATE_PROFILES, JOBS

    candidate_doc = await db[CANDIDATE_PROFILES].find_one({"user_id": candidate_id})
    if not candidate_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Please complete your profile first.",
        )

    try:
        oid = ObjectId(job_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job_id format.")

    job_doc = await db[JOBS].find_one({"_id": oid})
    if not job_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    result = match_candidate_to_job(candidate_doc, job_doc)

    return {
        "job_id": job_id,
        "job_title": job_doc.get("title", ""),
        **result,
    }
