from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from applications.schemas import ApplicationCreate, ApplicationStatusUpdate, ApplicationResponse

APPS = "applications"
JOBS = "jobs"
CANDIDATE_PROFILES = "candidate_profiles"
WORKFLOW_ORDER = ["applied", "under_review", "shortlisted", "interview"]
TERMINAL_STATUSES = {"selected", "rejected"}


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")


def _to_response(
    doc: dict,
    *,
    job_title: str | None = None,
    candidate_name: str | None = None,
    candidate_email: str | None = None,
    skills: list[str] | None = None,
    location: str | None = None,
    experience_years: float | None = None,
    education: str | None = None,
) -> ApplicationResponse:
    return ApplicationResponse(
        id=str(doc["_id"]),
        job_id=doc["job_id"],
        candidate_id=doc["candidate_id"],
        job_title=job_title,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        skills=skills or [],
        location=location,
        experience_years=experience_years,
        education=education,
        cover_letter=doc.get("cover_letter"),
        status=doc["status"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _build_enrichment_maps(
    docs: list[dict],
) -> tuple[
    dict[str, str | None],  # job_id -> title
    dict[str, str | None],  # candidate_id -> name
    dict[str, str | None],  # candidate_id -> email
    dict[str, dict],        # candidate_id -> profile fields
]:
    db = get_database()

    job_ids = []
    seen_job_ids: set = set()
    candidate_ids = []
    seen_candidate_ids: set = set()

    for doc in docs:
        job_id = doc.get("job_id")
        candidate_id = doc.get("candidate_id")

        if job_id and job_id not in seen_job_ids:
            seen_job_ids.add(job_id)
            try:
                job_ids.append(ObjectId(job_id))
            except Exception:
                pass

        if candidate_id and candidate_id not in seen_candidate_ids:
            seen_candidate_ids.add(candidate_id)
            candidate_ids.append(candidate_id)

    # jobs
    jobs_by_id: dict[str, str | None] = {}
    if job_ids:
        async for job in db[JOBS].find({"_id": {"$in": job_ids}}):
            jobs_by_id[str(job["_id"])] = job.get("title")

    # candidate names from profiles
    candidates_by_id: dict[str, str | None] = {}
    # candidate extra profile fields
    candidate_profiles: dict[str, dict] = {}
    if candidate_ids:
        async for profile in db[CANDIDATE_PROFILES].find({"user_id": {"$in": candidate_ids}}):
            uid = profile["user_id"]
            candidates_by_id[uid] = profile.get("full_name")
            candidate_profiles[uid] = {
                "skills": profile.get("skills") or [],
                "location": profile.get("location"),
                "experience_years": profile.get("experience_years"),
                "education": profile.get("education"),
            }

    # candidate emails from users collection
    candidate_emails: dict[str, str | None] = {}
    if candidate_ids:
        # user_id stored in candidate_profiles corresponds to _id in users
        user_object_ids = []
        for uid in candidate_ids:
            try:
                user_object_ids.append(ObjectId(uid))
            except Exception:
                pass
        if user_object_ids:
            async for user in db["users"].find({"_id": {"$in": user_object_ids}}):
                candidate_emails[str(user["_id"])] = user.get("email")

    return jobs_by_id, candidates_by_id, candidate_emails, candidate_profiles


async def _to_response_list(docs: list[dict]) -> list[ApplicationResponse]:
    jobs_by_id, candidates_by_id, candidate_emails, candidate_profiles = await _build_enrichment_maps(docs)
    return [
        _to_response(
            doc,
            job_title=jobs_by_id.get(doc["job_id"]),
            candidate_name=candidates_by_id.get(doc["candidate_id"]),
            candidate_email=candidate_emails.get(doc["candidate_id"]),
            **candidate_profiles.get(doc["candidate_id"], {}),
        )
        for doc in docs
    ]


async def _to_response_single(doc: dict) -> ApplicationResponse:
    jobs_by_id, candidates_by_id, candidate_emails, candidate_profiles = await _build_enrichment_maps([doc])
    return _to_response(
        doc,
        job_title=jobs_by_id.get(doc["job_id"]),
        candidate_name=candidates_by_id.get(doc["candidate_id"]),
        candidate_email=candidate_emails.get(doc["candidate_id"]),
        **candidate_profiles.get(doc["candidate_id"], {}),
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
    return await _to_response_single(doc)


async def get_my_applications(candidate_id: str) -> list[ApplicationResponse]:
    db = get_database()
    docs = [doc async for doc in db[APPS].find({"candidate_id": candidate_id})]
    return await _to_response_list(docs)


async def get_job_applications(job_id: str, hr_id: str) -> list[ApplicationResponse]:
    db = get_database()
    job = await db[JOBS].find_one({"_id": _oid(job_id)})
    if not job or job.get("hr_id") != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    docs = [doc async for doc in db[APPS].find({"job_id": job_id})]
    return await _to_response_list(docs)


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

    current_status = app["status"]
    new_status = data.status.value if hasattr(data.status, "value") else str(data.status)

    if current_status in TERMINAL_STATUSES and new_status != current_status:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Application is already {current_status} and cannot be moved to another status",
        )

    if current_status in WORKFLOW_ORDER and new_status in WORKFLOW_ORDER:
        if WORKFLOW_ORDER.index(new_status) < WORKFLOW_ORDER.index(current_status):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Cannot move application backward from {current_status} to {new_status}",
            )

    updated = await db[APPS].find_one_and_update(
        {"_id": app["_id"]},
        {"$set": {"status": data.status, "updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    return await _to_response_single(updated)


async def withdraw_application(app_id: str, candidate_id: str) -> dict:
    db = get_database()
    app = await db[APPS].find_one({"_id": _oid(app_id)})
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if app["candidate_id"] != candidate_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    await db[APPS].delete_one({"_id": app["_id"]})
    return {"message": "Application withdrawn successfully"}
