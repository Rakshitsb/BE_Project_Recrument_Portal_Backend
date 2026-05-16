import json
import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from config import settings
from database import get_database
from jobs.schemas import JobCreate, JobUpdate, JobResponse

COLLECTION = "jobs"
HR_PROFILES = "hr_profiles"
APPLICATIONS = "applications"
logger = logging.getLogger(__name__)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def _format_salary_range(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return cleaned
    if "lpa" in cleaned.lower():
        return cleaned
    return f"{cleaned} LPA"


def _to_response(doc: dict, hr_profile: dict | None = None) -> JobResponse:
    data = {k: v for k, v in doc.items() if k != "_id"}
    data["id"] = str(doc["_id"])
    data["title"] = _clean_text(doc.get("title")) or ""
    data["description"] = _clean_text(doc.get("description")) or ""
    data["required_skills"] = [skill.strip() for skill in (doc.get("required_skills") or [])]
    data["location"] = _clean_text(doc.get("location")) or ""
    data["job_type"] = _clean_text(doc.get("job_type")) or ""
    data["salary_range"] = _format_salary_range(doc.get("salary_range"))
    data["company_name"] = hr_profile.get("company_name") if hr_profile else None
    data["company_logo_url"] = (
        hr_profile.get("avatar_url") or hr_profile.get("profile_image", {}).get("url")
        if hr_profile else None
    )
    data["industry"] = hr_profile.get("industry") if hr_profile else None
    data["company_size"] = hr_profile.get("company_size") if hr_profile else None
    data["applicants"] = doc.get("applicants", 0)
    return JobResponse(**data)


def _object_id(job_id: str) -> ObjectId:
    try:
        return ObjectId(job_id)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid job ID format")


def _build_embedding_text(doc: dict) -> str:
    raw_jd_text = _clean_text(doc.get("raw_jd_text"))
    description = _clean_text(doc.get("description"))
    title = _clean_text(doc.get("title")) or "Job Description"
    jd_parsed = doc.get("jd_parsed")

    parts: list[str] = [title]
    if raw_jd_text:
        parts.append(raw_jd_text)
    if description and description != raw_jd_text:
        parts.append(description)
    if jd_parsed:
        try:
            parts.append(json.dumps(jd_parsed, ensure_ascii=False, sort_keys=True))
        except TypeError:
            logger.warning("Could not serialize jd_parsed for embedding generation")

    text = "\n\n".join(part for part in parts if part)
    return text.strip()


async def _sync_job_embedding(db, job_id: str, doc: dict) -> None:
    if not settings.ENABLE_EMBEDDING_SCORING:
        logger.info("Skipping embedding generation for job %s because embedding scoring is disabled", job_id)
        return

    embedding_text = _build_embedding_text(doc)
    if not embedding_text:
        logger.warning("Skipping embedding generation for job %s because no JD text was available", job_id)
        return
    from ai_services.vector_store import upsert_job_embedding

    await upsert_job_embedding(db, job_id, embedding_text)


async def create_job(hr_id: str, data: JobCreate) -> JobResponse:
    db = get_database()
    doc = {
        "hr_id": hr_id,
        "created_at": datetime.now(timezone.utc),
        **data.model_dump(),
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    try:
        await _sync_job_embedding(db, str(result.inserted_id), doc)
    except Exception as exc:
        await db[COLLECTION].delete_one({"_id": result.inserted_id})
        logger.exception("Failed to generate embedding for new job %s", result.inserted_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job was not created because JD embedding generation failed.",
        ) from exc
    hr_profile = await db[HR_PROFILES].find_one({"user_id": hr_id})
    return _to_response(doc, hr_profile=hr_profile)


async def get_all_jobs(hr_id: str | None = None) -> list[JobResponse]:
    db = get_database()
    query = {"is_active": True}
    if hr_id:
        query["hr_id"] = hr_id
    cursor = db[COLLECTION].find(query)
    responses = []
    async for doc in cursor:
        doc["applicants"] = await db[APPLICATIONS].count_documents({"job_id": str(doc["_id"])})
        hr_profile = await db[HR_PROFILES].find_one({"user_id": doc["hr_id"]})
        responses.append(_to_response(doc, hr_profile=hr_profile))
    return responses


async def get_job_by_id(job_id: str) -> JobResponse:
    db = get_database()
    doc = await db[COLLECTION].find_one({"_id": _object_id(job_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    doc["applicants"] = await db[APPLICATIONS].count_documents({"job_id": str(doc["_id"])})
    hr_profile = await db[HR_PROFILES].find_one({"user_id": doc["hr_id"]})
    return _to_response(doc, hr_profile=hr_profile)


async def update_job(job_id: str, hr_id: str, data: JobUpdate) -> JobResponse:
    db = get_database()
    col = db[COLLECTION]

    doc = await col.find_one({"_id": _object_id(job_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not authorized to update this job"
        )

    updates = data.model_dump(exclude_none=True)
    if updates:
        doc = await col.find_one_and_update(
            {"_id": doc["_id"]},
            {"$set": updates},
            return_document=True,
        )
        await _sync_job_embedding(db, str(doc["_id"]), doc)
    hr_profile = await db[HR_PROFILES].find_one({"user_id": hr_id})
    return _to_response(doc, hr_profile=hr_profile)


async def delete_job(job_id: str, hr_id: str) -> dict:
    db = get_database()
    col = db[COLLECTION]

    doc = await col.find_one({"_id": _object_id(job_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not authorized to delete this job"
        )

    await col.delete_one({"_id": doc["_id"]})
    if settings.ENABLE_EMBEDDING_SCORING:
        from ai_services.vector_store import delete_job_embedding

        await delete_job_embedding(str(doc["_id"]))
    return {"message": "Job deleted successfully"}
