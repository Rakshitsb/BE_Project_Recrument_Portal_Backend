import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from database import get_database
from db.collections import (
    APPLICATIONS, INTERVIEWS, INTERVIEWERS, JOBS,
)
from interview.schemas import (
    InterviewCreate, InterviewResponse, InterviewSummary,
)
from ai_services.interview_engine import generate_interview_questions


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(400, "Invalid ID format")


def _to_response(doc: dict) -> InterviewResponse:
    doc["id"] = str(doc.pop("_id"))
    return InterviewResponse(**doc)


def _to_summary(doc: dict) -> InterviewSummary:
    doc["id"] = str(doc.pop("_id"))
    return InterviewSummary(**doc)


async def create_interview(
    hr_id: str, data: InterviewCreate,
) -> InterviewResponse:
    db = get_database()
    app = await db[APPLICATIONS].find_one(
        {"_id": _oid(data.application_id)})
    if not app:
        raise HTTPException(404, "Application not found")
    job = await db[JOBS].find_one({"_id": _oid(app["job_id"])})
    if not job or job.get("hr_id") != hr_id:
        raise HTTPException(403, "Not authorized")
    if app["status"] != "shortlisted":
        raise HTTPException(
            400, "Candidate must be shortlisted before "
            "scheduling an interview")
    if await db[INTERVIEWS].find_one(
        {"application_id": data.application_id, "is_active": True}
    ):
        raise HTTPException(
            400, "An active interview already exists "
            "for this application")
    if not await db[INTERVIEWERS].find_one(
        {"_id": _oid(data.interviewer_id)}
    ):
        raise HTTPException(404, "Interviewer not found")
    ai = await generate_interview_questions(
        name=data.name, objective=data.objective,
        count=data.question_count, context=data.context)
    now = datetime.now(timezone.utc)
    doc = {
        "interview_token": secrets.token_urlsafe(32),
        "application_id": data.application_id,
        "job_id": app["job_id"], "hr_id": hr_id,
        "candidate_id": app["candidate_id"],
        "interviewer_id": data.interviewer_id,
        "name": data.name, "objective": data.objective,
        "description": ai["description"],
        "questions": ai["questions"],
        "question_count": data.question_count,
        "time_duration": data.time_duration,
        "is_active": True, "is_archived": False,
        "response_count": 0,
        "created_at": now, "updated_at": now,
    }
    result = await db[INTERVIEWS].insert_one(doc)
    doc["_id"] = result.inserted_id
    await db[APPLICATIONS].update_one(
        {"_id": _oid(data.application_id)},
        {"$set": {"status": "interview", "updated_at": now}})
    return _to_response(doc)
