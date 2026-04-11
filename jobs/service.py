from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from jobs.schemas import JobCreate, JobUpdate, JobResponse

COLLECTION = "jobs"
HR_PROFILES = "hr_profiles"


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
    return JobResponse(
        id=str(doc["_id"]),
        hr_id=doc["hr_id"],
        created_at=doc["created_at"],
        title=_clean_text(doc["title"]) or "",
        description=_clean_text(doc["description"]) or "",
        required_skills=[skill.strip() for skill in doc["required_skills"]],
        location=_clean_text(doc["location"]) or "",
        job_type=_clean_text(doc["job_type"]) or "",
        experience_required=doc["experience_required"],
        salary_range=_format_salary_range(doc.get("salary_range")),
        cover_letter_required=doc["cover_letter_required"],
        is_active=doc["is_active"],
        company_name=hr_profile.get("company_name") if hr_profile else None,
        industry=hr_profile.get("industry") if hr_profile else None,
        company_size=hr_profile.get("company_size") if hr_profile else None,
    )


def _object_id(job_id: str) -> ObjectId:
    try:
        return ObjectId(job_id)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid job ID format")


async def create_job(hr_id: str, data: JobCreate) -> JobResponse:
    db = get_database()
    doc = {"hr_id": hr_id, "created_at": datetime.now(timezone.utc), **data.model_dump()}
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    hr_profile = await db[HR_PROFILES].find_one({"user_id": hr_id})
    return _to_response(doc, hr_profile=hr_profile)


async def get_all_jobs() -> list[JobResponse]:
    db = get_database()
    cursor = db[COLLECTION].find({"is_active": True})
    responses = []
    async for doc in cursor:
        hr_profile = await db[HR_PROFILES].find_one({"user_id": doc["hr_id"]})
        responses.append(_to_response(doc, hr_profile=hr_profile))
    return responses


async def get_job_by_id(job_id: str) -> JobResponse:
    db = get_database()
    doc = await db[COLLECTION].find_one({"_id": _object_id(job_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    hr_profile = await db[HR_PROFILES].find_one({"user_id": doc["hr_id"]})
    return _to_response(doc, hr_profile=hr_profile)


async def update_job(job_id: str, hr_id: str, data: JobUpdate) -> JobResponse:
    db = get_database()
    col = db[COLLECTION]

    doc = await col.find_one({"_id": _object_id(job_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to update this job")

    updates = data.model_dump(exclude_none=True)
    if updates:
        doc = await col.find_one_and_update(
            {"_id": doc["_id"]},
            {"$set": updates},
            return_document=True,
        )
    hr_profile = await db[HR_PROFILES].find_one({"user_id": hr_id})
    return _to_response(doc, hr_profile=hr_profile)


async def delete_job(job_id: str, hr_id: str) -> dict:
    db = get_database()
    col = db[COLLECTION]

    doc = await col.find_one({"_id": _object_id(job_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to delete this job")

    await col.delete_one({"_id": doc["_id"]})
    return {"message": "Job deleted successfully"}
