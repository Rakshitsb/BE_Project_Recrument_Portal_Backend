from datetime import datetime, timezone

from fastapi import HTTPException, status

from database import get_database
from db.collections import APPLICATIONS, INTERVIEW_RESPONSES, INTERVIEWS
from interview_response.schemas import InterviewResponseOut, InterviewResponseSummary, ResponseStatusUpdate
from interview_response.service import _oid, _to_full, _to_summary, maybe_backfill_response_analysis


async def get_responses_by_interview(interview_id: str, hr_id: str) -> list[InterviewResponseSummary]:
    db = get_database()
    interview = await db[INTERVIEWS].find_one({"_id": _oid(interview_id)})
    if not interview:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if interview["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    now = datetime.now(timezone.utc)
    await db[INTERVIEW_RESPONSES].update_many({"interview_id": interview_id, "is_viewed": False, "is_ended": True}, {"$set": {"is_viewed": True, "updated_at": now}})
<<<<<<< HEAD
    docs = await db[INTERVIEW_RESPONSES].find({"interview_id": interview_id}).sort("created_at", -1).to_list(None)
=======
    docs = await db[INTERVIEW_RESPONSES].find({"interview_id": interview_id, "is_ended": True}).sort("created_at", -1).to_list(None)
>>>>>>> 6cda33488b4bb35745a77d86bee4a45713de2e6c
    return [_to_summary(doc | {"is_viewed": True if doc.get("is_ended") else doc.get("is_viewed", False), "updated_at": doc.get("updated_at", now)}) for doc in docs]


async def get_response_detail(response_id: str, hr_id: str) -> InterviewResponseOut:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one({"_id": _oid(response_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Response not found")
    interview = await db[INTERVIEWS].find_one({"_id": _oid(doc["interview_id"])})
    if not interview:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if interview["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
<<<<<<< HEAD
    doc = await maybe_backfill_response_analysis(doc)
=======
>>>>>>> 6cda33488b4bb35745a77d86bee4a45713de2e6c
    if not doc["is_viewed"]:
        now = datetime.now(timezone.utc)
        await db[INTERVIEW_RESPONSES].update_one({"_id": doc["_id"]}, {"$set": {"is_viewed": True, "updated_at": now}})
        doc["is_viewed"], doc["updated_at"] = True, now
    return _to_full(doc)


async def update_response_status(response_id: str, hr_id: str, data: ResponseStatusUpdate) -> InterviewResponseOut:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one({"_id": _oid(response_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Response not found")
    interview = await db[INTERVIEWS].find_one({"_id": _oid(doc["interview_id"])})
    if not interview:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if interview["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    now = datetime.now(timezone.utc)
    await db[INTERVIEW_RESPONSES].update_one({"_id": doc["_id"]}, {"$set": {"candidate_status": data.candidate_status, "updated_at": now}})
    if data.candidate_status in {"selected", "rejected"}:
        await db[APPLICATIONS].update_one({"_id": _oid(interview["application_id"])}, {"$set": {"status": data.candidate_status, "updated_at": now}})
    updated = await db[INTERVIEW_RESPONSES].find_one({"_id": doc["_id"]})
    return _to_full(updated)
