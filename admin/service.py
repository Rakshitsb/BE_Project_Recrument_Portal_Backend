import asyncio

from bson import ObjectId
from fastapi import HTTPException, status

from ai_services.vector_store import delete_job_embedding
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
    cursor = db[USERS].find({"role": "candidate"}, _NO_PW)
    return [_clean(doc) async for doc in cursor]


async def get_all_hrs() -> list[dict]:
    db = get_database()
    cursor = db[USERS].find({"role": "hr"}, _NO_PW)
    return [_clean(doc) async for doc in cursor]


async def get_all_jobs() -> list[dict]:
    db = get_database()
    cursor = db[JOBS].find()
    return [_clean(doc) async for doc in cursor]


async def get_all_applications() -> list[dict]:
    db = get_database()
    cursor = db[APPLICATIONS].find()
    return [_clean(doc) async for doc in cursor]


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

        # Remove in-memory vector entries for each deleted HR job.
        await asyncio.gather(*(delete_job_embedding(job_id) for job_id in job_ids))

    # Also remove any remaining chatbot sessions directly tied to the HR.
    await db[CHATBOT_SESSIONS].delete_many({"hr_id": user_id})

    # 6. Delete jobs, HR profile, and user account
    await db[JOBS].delete_many({"hr_id": user_id})
    await db[HR_PROFILES].delete_many({"user_id": user_id})
    await db[USERS].delete_one({"_id": user["_id"]})

    return {"message": "HR and all related data deleted successfully"}
