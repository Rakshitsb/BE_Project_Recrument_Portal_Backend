import json
import re
from typing import Any

from fastapi import HTTPException, status
from groq import AsyncGroq

from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

JD_PARSER_PROMPT = """
You are an expert job description parser.

Extract the job description into structured JSON.

Rules:
- No preamble, no markdown, no backticks, no explanation
- Return ONLY one valid JSON object
- Use a dynamic structure based on the document; do not force a rigid schema
- Include common hiring fields when available, such as title, summary, description,
  responsibilities, required_skills, nice_to_have_skills, experience_required,
  education_required, job_type, location, salary_range, company_culture, keywords
- Preserve additional useful fields when present, such as department, benefits,
  certifications, work_mode, shift, notice_period, industry, reporting_manager,
  tools, languages, domain_experience, screening_questions, etc.
- Use arrays for multi-value sections and nested objects when that is clearer
- If a value is missing, prefer omitting the key rather than inventing data
- Keywords should help semantic job matching and be max 20 items
"""


async def parse_jd_with_groq(jd_text: str) -> dict[str, Any]:
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
        if not isinstance(parsed, dict):
            raise ValueError("Model returned non-object JSON")
        if isinstance(parsed.get("keywords"), list):
            parsed["keywords"] = parsed["keywords"][:20]
        return parsed
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
