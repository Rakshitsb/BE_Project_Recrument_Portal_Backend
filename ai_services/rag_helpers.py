"""
RAG Chatbot — Private MongoDB Fetch Helpers
============================================
These are the three async helpers used by rag_chatbot.get_chatbot_response()
to pull context from MongoDB.  They are kept in a separate file so that
rag_chatbot.py stays under 150 lines.

All functions return plain dicts (no Pydantic) and degrade gracefully to an
empty dict when a document is not found or an ObjectId is invalid.
"""

import logging
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from db.collections import CANDIDATE_PROFILES, HR_PROFILES, JOBS

logger = logging.getLogger(__name__)


async def _fetch_job_with_hr(db: Any, job_id: str) -> dict:
    """Fetch a job document and return title, hr_id, and jd_parsed.

    Args:
        db:     Motor async database instance.
        job_id: String form of the job's MongoDB ObjectId.

    Returns:
        Dict with keys ``title``, ``hr_id``, ``jd_parsed``.
        Returns ``{}`` if not found or if job_id is an invalid ObjectId.
    """
    try:
        oid = ObjectId(job_id)
    except (InvalidId, TypeError):
        logger.warning("[RAGHelpers] Invalid job_id: %s", job_id)
        return {}

    doc = await db[JOBS].find_one(
        {"_id": oid},
        {"title": 1, "hr_id": 1, "jd_parsed": 1},
    )
    if not doc:
        return {}

    return {
        "title": doc.get("title", ""),
        "hr_id": doc.get("hr_id", ""),
        "jd_parsed": doc.get("jd_parsed"),  # may be None
    }


async def _fetch_hr_profile(db: Any, hr_id: str) -> dict:
    """Fetch an HR profile by user_id and return company info fields.

    Args:
        db:    Motor async database instance.
        hr_id: The ``user_id`` field stored in the hr_profiles collection.

    Returns:
        Dict with keys: ``company_name``, ``industry``, ``company_size``,
        ``company_location``, ``company_website``.
        Returns ``{}`` if not found.
    """
    if not hr_id:
        return {}

    doc = await db[HR_PROFILES].find_one(
        {"user_id": hr_id},
        {
            "company_name": 1,
            "industry": 1,
            "company_size": 1,
            "company_location": 1,
            "company_website": 1,
        },
    )
    if not doc:
        return {}

    return {
        "company_name": doc.get("company_name", ""),
        "industry": doc.get("industry", ""),
        "company_size": doc.get("company_size", ""),
        "company_location": doc.get("company_location", ""),
        "company_website": doc.get("company_website", ""),
    }


async def _fetch_candidate_profile(db: Any, candidate_id: str) -> dict:
    """Fetch a candidate profile by user_id and return key profile fields.

    Only the last 2 experience entries are returned to keep the context
    window manageable.

    Args:
        db:           Motor async database instance.
        candidate_id: The ``user_id`` field stored in candidate_profiles.

    Returns:
        Dict with keys: ``full_name``, ``skills``, ``experience_years``,
        ``education``, ``experience`` (last 2 entries).
        Returns ``{}`` if not found.
    """
    if not candidate_id:
        return {}

    doc = await db[CANDIDATE_PROFILES].find_one(
        {"user_id": candidate_id},
        {
            "full_name": 1,
            "skills": 1,
            "experience_years": 1,
            "education": 1,
            "experience": 1,
        },
    )
    if not doc:
        return {}

    experience_raw = doc.get("experience") or []
    # Keep only the two most-recent entries to limit prompt size
    recent_experience = experience_raw[-2:] if len(experience_raw) > 2 else experience_raw

    return {
        "full_name": doc.get("full_name", ""),
        "skills": doc.get("skills") or [],
        "experience_years": doc.get("experience_years", 0),
        "education": doc.get("education") or "",
        "experience": recent_experience,
    }
