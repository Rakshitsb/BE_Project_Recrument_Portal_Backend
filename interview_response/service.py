from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from config import settings
from database import get_database
from db.collections import INTERVIEW_RESPONSES, INTERVIEWS
from interview_response.schemas import AnalyticsOut, CandidateResponseOut, InterviewResponseOut, InterviewResponseSummary, TabSwitchUpdate
from retell_sdk import Retell

retell_client = Retell(api_key=settings.RETELL_API_KEY) if settings.RETELL_API_KEY else None


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")


def _analytics(doc: dict) -> AnalyticsOut | None:
    try:
        return AnalyticsOut(**doc["analytics"]) if isinstance(doc.get("analytics"), dict) else None
    except Exception:
        return None


def _to_full(doc: dict) -> InterviewResponseOut:
    return InterviewResponseOut(id=str(doc["_id"]), interview_id=doc["interview_id"], candidate_id=doc["candidate_id"], call_id=doc["call_id"], name=doc.get("name"), email=doc.get("email"), duration=doc.get("duration"), analytics=_analytics(doc), candidate_status=doc["candidate_status"], is_analysed=doc["is_analysed"], is_ended=doc["is_ended"], is_viewed=doc["is_viewed"], tab_switch_count=doc.get("tab_switch_count", 0), created_at=doc["created_at"], updated_at=doc["updated_at"])


def _to_summary(doc: dict) -> InterviewResponseSummary:
    return InterviewResponseSummary(id=str(doc["_id"]), interview_id=doc["interview_id"], candidate_id=doc["candidate_id"], call_id=doc["call_id"], name=doc.get("name"), email=doc.get("email"), duration=doc.get("duration"), candidate_status=doc["candidate_status"], is_analysed=doc["is_analysed"], is_ended=doc["is_ended"], is_viewed=doc["is_viewed"], tab_switch_count=doc.get("tab_switch_count", 0), created_at=doc["created_at"])


def _to_candidate(doc: dict) -> CandidateResponseOut:
    return CandidateResponseOut(id=str(doc["_id"]), interview_id=doc["interview_id"], call_id=doc["call_id"], name=doc.get("name"), duration=doc.get("duration"), analytics=_analytics(doc) if doc.get("is_analysed") else None, is_analysed=doc["is_analysed"], is_ended=doc["is_ended"], created_at=doc["created_at"])


async def maybe_backfill_response_analysis(doc: dict) -> dict:
    if not doc or not doc.get("is_ended") or doc.get("is_analysed"):
        return doc

    db = get_database()
    try:
        interview_doc = await db[INTERVIEWS].find_one({"_id": _oid(doc["interview_id"])})
    except HTTPException:
        return doc
    if not interview_doc:
        return doc

    call_payload = doc.get("details") if isinstance(doc.get("details"), dict) else None
    transcript = call_payload.get("transcript") if call_payload else None

    if not transcript and retell_client and doc.get("call_id"):
        try:
            fetched_call = retell_client.call.retrieve(doc["call_id"])
            if hasattr(fetched_call, "model_dump"):
                call_payload = fetched_call.model_dump()
            elif isinstance(fetched_call, dict):
                call_payload = fetched_call
            else:
                call_payload = {
                    "call_id": getattr(fetched_call, "call_id", doc.get("call_id")),
                    "transcript": getattr(fetched_call, "transcript", None),
                    "start_timestamp": getattr(fetched_call, "start_timestamp", None),
                    "end_timestamp": getattr(fetched_call, "end_timestamp", None),
                }
            transcript = (call_payload or {}).get("transcript")
        except Exception:
            return doc

    if not transcript:
        return doc

    questions = interview_doc.get("questions", [])
    question_texts = [q["question"] for q in questions if isinstance(q, dict) and q.get("question")]

    try:
        from ai_services.analytics_engine import analyze_transcript

        analytics = await analyze_transcript(transcript=transcript, questions=question_texts)
    except Exception:
        return doc

    updates = {
        "analytics": analytics,
        "details": call_payload,
        "is_analysed": True,
        "is_ended": True,
        "updated_at": datetime.now(timezone.utc),
    }
    if not doc.get("duration") and call_payload:
        start_ts = call_payload.get("start_timestamp")
        end_ts = call_payload.get("end_timestamp")
        if start_ts and end_ts:
            updates["duration"] = round((end_ts - start_ts) / 1000)

    await db[INTERVIEW_RESPONSES].update_one({"_id": doc["_id"]}, {"$set": updates})
    updated = await db[INTERVIEW_RESPONSES].find_one({"_id": doc["_id"]})
    return updated or doc


async def get_my_response(interview_id: str, candidate_id: str) -> CandidateResponseOut:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one(
        {"interview_id": interview_id, "candidate_id": candidate_id, "is_ended": True},
        sort=[("created_at", -1)],
    )
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No completed interview found")
    doc = await maybe_backfill_response_analysis(doc)
    return _to_candidate(doc)


async def record_tab_switch(call_id: str, candidate_id: str, data: TabSwitchUpdate) -> dict:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one({"call_id": call_id, "candidate_id": candidate_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Response not found")
    if doc["candidate_id"] != candidate_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    await db[INTERVIEW_RESPONSES].update_one({"_id": doc["_id"]}, {"$set": {"tab_switch_count": data.count}})
    return {"message": "Tab switch count updated", "count": data.count}
