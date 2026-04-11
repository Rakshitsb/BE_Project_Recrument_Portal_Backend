"""Interview get, list, update, and delete operations."""
from datetime import datetime, timezone

from fastapi import HTTPException

from database import get_database
from db.collections import INTERVIEWS
from interview.schemas import (
    InterviewResponse, InterviewSummary, InterviewUpdate,
)
from interview.service import _oid, _to_response, _to_summary
from ai_services.interview_engine import generate_interview_questions


async def get_interview_by_id(
    interview_id: str, hr_id: str,
) -> InterviewResponse:
    db = get_database()
    doc = await db[INTERVIEWS].find_one(
        {"_id": _oid(interview_id)})
    if not doc:
        raise HTTPException(404, "Interview not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(403, "Not authorized")
    return _to_response(doc)


async def list_interviews_by_hr(
    hr_id: str,
) -> list[InterviewSummary]:
    db = get_database()
    cursor = db[INTERVIEWS].find(
        {"hr_id": hr_id, "is_archived": False}
    ).sort("created_at", -1)
    return [_to_summary(doc) async for doc in cursor]


async def update_interview(
    interview_id: str, hr_id: str, data: InterviewUpdate,
) -> InterviewResponse:
    db = get_database()
    doc = await db[INTERVIEWS].find_one(
        {"_id": _oid(interview_id)})
    if not doc:
        raise HTTPException(404, "Interview not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(403, "Not authorized")
    updates = data.model_dump(
        exclude_none=True,
        exclude={"regenerate_questions", "context"})
    if data.regenerate_questions:
        name = data.name or doc["name"]
        objective = data.objective or doc["objective"]
        ai = await generate_interview_questions(
            name=name, objective=objective,
            count=doc["question_count"], context=data.context)
        updates["questions"] = ai["questions"]
        updates["description"] = ai["description"]
    updates["updated_at"] = datetime.now(timezone.utc)
    updated = await db[INTERVIEWS].find_one_and_update(
        {"_id": doc["_id"]}, {"$set": updates},
        return_document=True)
    return _to_response(updated)


async def delete_interview(
    interview_id: str, hr_id: str,
) -> dict:
    db = get_database()
    doc = await db[INTERVIEWS].find_one(
        {"_id": _oid(interview_id)})
    if not doc:
        raise HTTPException(404, "Interview not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(403, "Not authorized")
    await db[INTERVIEWS].update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_active": False, "is_archived": True,
                  "updated_at": datetime.now(timezone.utc)}})
    return {"message": "Interview archived successfully"}
