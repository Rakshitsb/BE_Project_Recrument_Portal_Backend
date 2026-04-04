from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from applications.schemas import ApplicationCreate, ApplicationStatusUpdate, ApplicationResponse

APPS = "applications"
JOBS = "jobs"


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")


def _to_response(doc: dict) -> ApplicationResponse:
    return ApplicationResponse(
        id=str(doc["_id"]),
        job_id=doc["job_id"],
        candidate_id=doc["candidate_id"],
        cover_letter=doc.get("cover_letter"),
        status=doc["status"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_application(candidate_id: str, data: ApplicationCreate) -> ApplicationResponse:
    db = get_database()
    now = datetime.now(timezone.utc)

    job = await db[JOBS].find_one({"_id": _oid(data.job_id)})
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.get("cover_letter_required") and not data.cover_letter:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cover letter is required for this job")
    if await db[APPS].find_one({"job_id": data.job_id, "candidate_id": candidate_id}):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already applied to this job")

    doc = {
        "job_id": data.job_id,
        "candidate_id": candidate_id,
        "cover_letter": data.cover_letter,
        "status": "applied",
        "created_at": now,
        "updated_at": now,
    }
    result = await db[APPS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def get_my_applications(candidate_id: str) -> list[ApplicationResponse]:
    db = get_database()
    cursor = db[APPS].find({"candidate_id": candidate_id})
    return [_to_response(doc) async for doc in cursor]


async def get_job_applications(job_id: str, hr_id: str) -> list[ApplicationResponse]:
    db = get_database()
    job = await db[JOBS].find_one({"_id": _oid(job_id)})
    if not job or job.get("hr_id") != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    cursor = db[APPS].find({"job_id": job_id})
    return [_to_response(doc) async for doc in cursor]


async def update_application_status(
    app_id: str, hr_id: str, data: ApplicationStatusUpdate
) -> ApplicationResponse:
    db = get_database()
    app = await db[APPS].find_one({"_id": _oid(app_id)})
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")

    job = await db[JOBS].find_one({"_id": _oid(app["job_id"])})
    if not job or job.get("hr_id") != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    updated = await db[APPS].find_one_and_update(
        {"_id": app["_id"]},
        {"$set": {"status": data.status, "updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    return _to_response(updated)


async def withdraw_application(app_id: str, candidate_id: str) -> dict:
    db = get_database()
    app = await db[APPS].find_one({"_id": _oid(app_id)})
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if app["candidate_id"] != candidate_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    await db[APPS].delete_one({"_id": app["_id"]})
    return {"message": "Application withdrawn successfully"}
