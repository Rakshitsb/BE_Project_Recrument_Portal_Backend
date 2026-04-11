from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from db.collections import INTERVIEW_RESPONSES, INTERVIEWS
from retell.logging import logger
from retell.schemas import RetellCallPayload


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")


async def handle_call_analyzed(call: RetellCallPayload) -> None:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one({"call_id": call.call_id})
    if not doc:
        logger.warning("No response doc for call %s", call.call_id)
        return
    if doc.get("is_analysed") is True:
        return
    try:
        interview_doc = await db[INTERVIEWS].find_one({"_id": _oid(doc["interview_id"])})
    except HTTPException:
        logger.warning("Interview %s not found for call %s", doc.get("interview_id"), call.call_id)
        return
    if not interview_doc:
        logger.warning("Interview %s not found for call %s", doc.get("interview_id"), call.call_id)
        return
    transcript = call.transcript or ""
    if not transcript:
        logger.warning("Empty transcript for call %s, skipping analytics", call.call_id)
        return
    questions = interview_doc.get("questions", [])
    question_texts = [q["question"] for q in questions]
    call_dict = call.model_dump()
    try:
        from ai_services.analytics_engine import analyze_transcript
        analytics = await analyze_transcript(transcript=transcript, questions=question_texts)
        await db[INTERVIEW_RESPONSES].update_one(
            {"call_id": call.call_id},
            {"$set": {
                "details": call_dict,
                "analytics": analytics,
                "is_analysed": True,
                "is_ended": True,
                "updated_at": datetime.now(timezone.utc),
            }},
        )
    except Exception as e:
        logger.error("Analytics failed for call %s: %s", call.call_id, e)
        await db[INTERVIEW_RESPONSES].update_one(
            {"call_id": call.call_id},
            {"$set": {
                "details": call_dict,
                "is_ended": True,
                "updated_at": datetime.now(timezone.utc),
            }},
        )
