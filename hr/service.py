from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from hr.schemas import (
    HRDashboardApplication,
    HRDashboardJob,
    HRDashboardResponse,
    HRDashboardStats,
    HRProfileCreate,
    HRProfileResponse,
    HRProfileUpdate,
)

COLLECTION = "hr_profiles"
JOBS = "jobs"
APPLICATIONS = "applications"
CANDIDATE_PROFILES = "candidate_profiles"
USERS = "users"


def _to_response(doc: dict) -> HRProfileResponse:
    return HRProfileResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        created_at=doc["created_at"],
        **{k: doc[k] for k in HRProfileCreate.model_fields},
    )


def _status_value(status_value) -> str:
    if hasattr(status_value, "value"):
        return status_value.value
    return str(status_value or "applied")


async def create_profile(user_id: str, data: HRProfileCreate) -> HRProfileResponse:
    db = get_database()
    col = db[COLLECTION]

    existing = await col.find_one({"user_id": user_id})
    if existing:
        # Profile already exists — update it in place (upsert behaviour)
        updates = data.model_dump(exclude_none=True)
        result = await col.find_one_and_update(
            {"user_id": user_id},
            {"$set": updates},
            return_document=True,
        )
        return _to_response(result)

    doc = {"user_id": user_id, "created_at": datetime.now(timezone.utc), **data.model_dump()}
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def get_profile(user_id: str) -> HRProfileResponse:
    db = get_database()
    doc = await db[COLLECTION].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return _to_response(doc)


async def update_profile(user_id: str, data: HRProfileUpdate) -> HRProfileResponse:
    db = get_database()
    col = db[COLLECTION]

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return await get_profile(user_id)

    result = await col.find_one_and_update(
        {"user_id": user_id},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return _to_response(result)


async def delete_profile(user_id: str) -> dict:
    db = get_database()
    result = await db[COLLECTION].find_one_and_delete({"user_id": user_id})
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return {"message": "Profile deleted successfully"}


async def get_dashboard(user_id: str) -> HRDashboardResponse:
    db = get_database()
    job_docs = [
        doc
        async for doc in db[JOBS]
        .find({"hr_id": user_id})
        .sort("created_at", -1)
    ]
    job_ids = [str(doc["_id"]) for doc in job_docs]

    applicant_counts: dict[str, int] = {}
    selected_count = 0
    if job_ids:
        applicant_pipeline = [
            {"$match": {"job_id": {"$in": job_ids}}},
            {"$group": {"_id": "$job_id", "count": {"$sum": 1}}},
        ]
        async for item in db[APPLICATIONS].aggregate(applicant_pipeline):
            applicant_counts[str(item["_id"])] = item["count"]

        selected_count = await db[APPLICATIONS].count_documents({
            "job_id": {"$in": job_ids},
            "status": "selected",
        })

    active_jobs = [doc for doc in job_docs if doc.get("is_active", True)]
    jobs = [
        HRDashboardJob(
            id=str(doc["_id"]),
            title=doc.get("title") or "",
            is_active=doc.get("is_active", True),
            applicants=applicant_counts.get(str(doc["_id"]), 0),
            created_at=doc["created_at"],
        )
        for doc in active_jobs
    ]

    recent_docs = []
    if job_ids:
        recent_docs = [
            doc
            async for doc in db[APPLICATIONS]
            .find({"job_id": {"$in": job_ids}})
            .sort("created_at", -1)
            .limit(5)
        ]

    jobs_by_id = {str(doc["_id"]): doc for doc in job_docs}
    candidate_ids = sorted({
        doc.get("candidate_id")
        for doc in recent_docs
        if doc.get("candidate_id")
    })

    profiles_by_user_id: dict[str, dict] = {}
    if candidate_ids:
        async for profile in db[CANDIDATE_PROFILES].find({"user_id": {"$in": candidate_ids}}):
            profiles_by_user_id[profile["user_id"]] = profile

    users_by_id: dict[str, dict] = {}
    candidate_object_ids = []
    for candidate_id in candidate_ids:
        try:
            candidate_object_ids.append(ObjectId(candidate_id))
        except Exception:
            pass
    if candidate_object_ids:
        async for user in db[USERS].find({"_id": {"$in": candidate_object_ids}}):
            users_by_id[str(user["_id"])] = user

    recent_applicants = []
    for doc in recent_docs:
        candidate_id = doc.get("candidate_id")
        profile = profiles_by_user_id.get(candidate_id, {})
        user = users_by_id.get(candidate_id, {})
        job = jobs_by_id.get(doc.get("job_id"), {})
        recent_applicants.append(
            HRDashboardApplication(
                id=str(doc["_id"]),
                job_id=doc["job_id"],
                candidate_id=candidate_id,
                job_title=job.get("title"),
                candidate_name=profile.get("full_name") or user.get("name") or user.get("email"),
                candidate_email=user.get("email"),
                status=_status_value(doc.get("status")),
                created_at=doc["created_at"],
            )
        )

    stats = HRDashboardStats(
        total_jobs_posted=len(job_docs),
        active_jobs=len(active_jobs),
        total_applicants=sum(applicant_counts.values()),
        positions_filled=selected_count,
    )
    return HRDashboardResponse(
        stats=stats,
        jobs=jobs,
        recent_applicants=recent_applicants,
    )
