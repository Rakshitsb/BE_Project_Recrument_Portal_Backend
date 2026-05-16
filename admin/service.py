import asyncio

from bson import ObjectId
from fastapi import HTTPException, status

from config import settings
from database import get_database
from db.collections import (
    APPLICATIONS,
    CANDIDATE_PROFILES,
    CHATBOT_SESSIONS,
    HR_PROFILES,
    INTERVIEW_FEEDBACK,
    INTERVIEW_RESPONSES,
    INTERVIEWS,
    JOBS,
    USERS,
)

_NO_PW = {"hashed_password": 0}


def _oid(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")


def _clean(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


async def get_all_candidates() -> list[dict]:
    db = get_database()
    users = [doc async for doc in db[USERS].find({"role": "candidate"}, _NO_PW)]
    if not users:
        return []

    user_ids = [str(user["_id"]) for user in users]

    profiles: dict[str, dict] = {}
    async for profile in db[CANDIDATE_PROFILES].find({"user_id": {"$in": user_ids}}):
        profiles[profile["user_id"]] = profile

    application_counts: dict[str, int] = {}
    pipeline = [
        {"$group": {"_id": "$candidate_id", "count": {"$sum": 1}}},
    ]
    async for item in db[APPLICATIONS].aggregate(pipeline):
        application_counts[str(item["_id"])] = item["count"]

    candidates = []
    for user in users:
        candidate = _clean(user)
        profile = profiles.get(candidate["id"], {})

        candidate["full_name"] = profile.get("full_name") or candidate.get("name")
        candidate["phone"] = profile.get("phone")
        candidate["location"] = profile.get("location")
        candidate["skills"] = profile.get("skills") or []
        candidate["experience_years"] = profile.get("experience_years", 0)
        candidate["education"] = profile.get("education")
        candidate["bio"] = profile.get("bio")
        candidate["created_at"] = profile.get("created_at") or candidate.get("created_at")
        candidate["total_applications"] = application_counts.get(candidate["id"], 0)
        candidate["status"] = "active"
        candidates.append(candidate)

    return candidates


async def get_all_hrs() -> list[dict]:
    db = get_database()
    users = [doc async for doc in db[USERS].find({"role": "hr"}, _NO_PW)]
    if not users:
        return []

    user_ids = [str(user["_id"]) for user in users]

    profiles: dict[str, dict] = {}
    async for profile in db[HR_PROFILES].find({"user_id": {"$in": user_ids}}):
        profiles[profile["user_id"]] = profile

    job_counts: dict[str, int] = {}
    pipeline = [
        {"$group": {"_id": "$hr_id", "count": {"$sum": 1}}},
    ]
    async for item in db[JOBS].aggregate(pipeline):
        job_counts[str(item["_id"])] = item["count"]

    hrs = []
    for user in users:
        hr = _clean(user)
        profile = profiles.get(hr["id"], {})

        hr["full_name"] = profile.get("full_name") or hr.get("name")
        hr["phone"] = profile.get("phone")
        hr["designation"] = profile.get("designation")
        hr["company_name"] = profile.get("company_name")
        hr["company_location"] = profile.get("company_location")
        hr["industry"] = profile.get("industry")
        hr["company_size"] = profile.get("company_size")
        hr["company_website"] = profile.get("company_website")
        hr["created_at"] = profile.get("created_at") or hr.get("created_at")
        hr["total_jobs_posted"] = job_counts.get(hr["id"], 0)
        hr["status"] = "active"
        hrs.append(hr)

    return hrs


async def get_all_jobs() -> list[dict]:
    db = get_database()
    docs = [doc async for doc in db[JOBS].find()]
    if not docs:
        return []

    hr_ids = sorted({doc.get("hr_id") for doc in docs if doc.get("hr_id")})

    hr_profiles: dict[str, dict] = {}
    if hr_ids:
        async for profile in db[HR_PROFILES].find({"user_id": {"$in": hr_ids}}):
            hr_profiles[profile["user_id"]] = profile

    hr_users: dict[str, dict] = {}
    user_object_ids = []
    for hr_id in hr_ids:
        try:
            user_object_ids.append(ObjectId(hr_id))
        except Exception:
            pass
    if user_object_ids:
        async for user in db[USERS].find({"_id": {"$in": user_object_ids}}, _NO_PW):
            hr_users[str(user["_id"])] = user

    applicant_counts: dict[str, int] = {}
    pipeline = [
        {"$group": {"_id": "$job_id", "count": {"$sum": 1}}},
    ]
    async for item in db[APPLICATIONS].aggregate(pipeline):
        applicant_counts[str(item["_id"])] = item["count"]

    jobs = []
    for doc in docs:
        job = _clean(doc)
        hr_id = job.get("hr_id")
        profile = hr_profiles.get(hr_id, {})
        user = hr_users.get(hr_id, {})

        job["company_name"] = profile.get("company_name")
        job["hr_name"] = profile.get("full_name") or user.get("name") or user.get("email")
        job["applicants"] = applicant_counts.get(job["id"], 0)
        jobs.append(job)

    return jobs


async def get_all_applications() -> list[dict]:
    db = get_database()
    docs = [doc async for doc in db[APPLICATIONS].find()]
    if not docs:
        return []

    job_object_ids = []
    candidate_object_ids = []
    candidate_ids = []
    seen_job_ids: set[str] = set()
    seen_candidate_ids: set[str] = set()

    for doc in docs:
        job_id = doc.get("job_id")
        candidate_id = doc.get("candidate_id")

        if job_id and job_id not in seen_job_ids:
            seen_job_ids.add(job_id)
            try:
                job_object_ids.append(ObjectId(job_id))
            except Exception:
                pass

        if candidate_id and candidate_id not in seen_candidate_ids:
            seen_candidate_ids.add(candidate_id)
            candidate_ids.append(candidate_id)
            try:
                candidate_object_ids.append(ObjectId(candidate_id))
            except Exception:
                pass

    jobs_by_id: dict[str, dict] = {}
    if job_object_ids:
        async for job in db[JOBS].find({"_id": {"$in": job_object_ids}}):
            jobs_by_id[str(job["_id"])] = job

    candidate_profiles: dict[str, dict] = {}
    if candidate_ids:
        async for profile in db[CANDIDATE_PROFILES].find({"user_id": {"$in": candidate_ids}}):
            candidate_profiles[profile["user_id"]] = profile

    candidate_users: dict[str, dict] = {}
    if candidate_object_ids:
        async for user in db[USERS].find({"_id": {"$in": candidate_object_ids}}, _NO_PW):
            candidate_users[str(user["_id"])] = user

    hr_ids = sorted({job.get("hr_id") for job in jobs_by_id.values() if job.get("hr_id")})

    hr_profiles: dict[str, dict] = {}
    if hr_ids:
        async for profile in db[HR_PROFILES].find({"user_id": {"$in": hr_ids}}):
            hr_profiles[profile["user_id"]] = profile

    hr_users: dict[str, dict] = {}
    hr_object_ids = []
    for hr_id in hr_ids:
        try:
            hr_object_ids.append(ObjectId(hr_id))
        except Exception:
            pass
    if hr_object_ids:
        async for user in db[USERS].find({"_id": {"$in": hr_object_ids}}, _NO_PW):
            hr_users[str(user["_id"])] = user

    applications = []
    for doc in docs:
        application = _clean(doc)
        job = jobs_by_id.get(application.get("job_id"), {})
        candidate_profile = candidate_profiles.get(application.get("candidate_id"), {})
        candidate_user = candidate_users.get(application.get("candidate_id"), {})
        hr_id = job.get("hr_id")
        hr_profile = hr_profiles.get(hr_id, {})
        hr_user = hr_users.get(hr_id, {})

        application["job_title"] = job.get("title")
        application["candidate_name"] = (
            candidate_profile.get("full_name")
            or candidate_user.get("name")
            or candidate_user.get("email")
        )
        application["candidate_email"] = candidate_user.get("email")
        application["company_name"] = hr_profile.get("company_name")
        application["hr_name"] = (
            hr_profile.get("full_name")
            or hr_user.get("name")
            or hr_user.get("email")
        )
        application["experience_years"] = candidate_profile.get("experience_years")
        application["location"] = candidate_profile.get("location") or job.get("location")
        applications.append(application)

    return applications


async def delete_candidate(user_id: str) -> dict:
    db = get_database()

    user = await db[USERS].find_one({"_id": _oid(user_id)}, _NO_PW)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    if user.get("role") != "candidate":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not a candidate")

    # 1. Delete candidate's interview responses and feedback
    #    (Do NOT delete the interview itself — it belongs to HR)
    await db[INTERVIEW_RESPONSES].delete_many({"candidate_id": user_id})
    await db[INTERVIEW_FEEDBACK].delete_many({"candidate_id": user_id})

    # 2. Delete candidate's applications
    await db[APPLICATIONS].delete_many({"candidate_id": user_id})

    # 3. Delete candidate chatbot sessions
    await db[CHATBOT_SESSIONS].delete_many({"candidate_id": user_id})

    # 4. Delete candidate profile and user account
    await db[CANDIDATE_PROFILES].delete_many({"user_id": user_id})
    await db[USERS].delete_one({"_id": user["_id"]})

    return {"message": "Candidate and all related data deleted successfully"}


async def delete_hr(user_id: str) -> dict:
    db = get_database()

    user = await db[USERS].find_one({"_id": _oid(user_id)}, _NO_PW)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "HR not found")
    if user.get("role") != "hr":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not an HR")

    # 1. Collect all interview IDs created by this HR
    interview_ids = [
        str(doc["_id"])
        async for doc in db[INTERVIEWS].find({"hr_id": user_id}, {"_id": 1})
    ]

    # 2. Delete interview responses and feedback for those interviews
    if interview_ids:
        await db[INTERVIEW_RESPONSES].delete_many({"interview_id": {"$in": interview_ids}})
        await db[INTERVIEW_FEEDBACK].delete_many({"interview_id": {"$in": interview_ids}})

    # 3. Delete all interviews created by this HR
    await db[INTERVIEWS].delete_many({"hr_id": user_id})

    # 4. Collect all job IDs posted by this HR
    job_ids = [
        str(doc["_id"])
        async for doc in db[JOBS].find({"hr_id": user_id}, {"_id": 1})
    ]

    # 5. Delete applications and chatbot sessions for those jobs / this HR
    if job_ids:
        await db[APPLICATIONS].delete_many({"job_id": {"$in": job_ids}})
        await db[CHATBOT_SESSIONS].delete_many({"job_id": {"$in": job_ids}})

        if settings.ENABLE_EMBEDDING_SCORING:
            from ai_services.vector_store import delete_job_embedding

            # Remove in-memory vector entries for each deleted HR job.
            await asyncio.gather(*(delete_job_embedding(job_id) for job_id in job_ids))

    # Also remove any remaining chatbot sessions directly tied to the HR.
    await db[CHATBOT_SESSIONS].delete_many({"hr_id": user_id})

    # 6. Delete jobs, HR profile, and user account
    await db[JOBS].delete_many({"hr_id": user_id})
    await db[HR_PROFILES].delete_many({"user_id": user_id})
    await db[USERS].delete_one({"_id": user["_id"]})

    return {"message": "HR and all related data deleted successfully"}
