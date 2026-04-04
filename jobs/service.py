from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from jobs.schemas import JobCreate, JobUpdate, JobResponse

COLLECTION = "jobs"


def _to_response(doc: dict) -> JobResponse:
    return JobResponse(
        id=str(doc["_id"]),
        hr_id=doc["hr_id"],
        created_at=doc["created_at"],
        **{k: doc[k] for k in JobCreate.model_fields},
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
    return _to_response(doc)


async def get_all_jobs() -> list[JobResponse]:
    db = get_database()
    cursor = db[COLLECTION].find({"is_active": True})
    return [_to_response(doc) async for doc in cursor]


async def get_job_by_id(job_id: str) -> JobResponse:
    db = get_database()
    doc = await db[COLLECTION].find_one({"_id": _object_id(job_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return _to_response(doc)


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
    return _to_response(doc)


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
