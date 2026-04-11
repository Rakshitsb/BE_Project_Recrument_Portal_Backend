from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from db.collections import INTERVIEW_RESPONSES
from interview_response.schemas import AnalyticsOut, CandidateResponseOut, InterviewResponseOut, InterviewResponseSummary, TabSwitchUpdate


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


async def get_my_response(interview_id: str, candidate_id: str) -> CandidateResponseOut:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one({"interview_id": interview_id, "candidate_id": candidate_id, "is_ended": True})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No completed interview found")
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
