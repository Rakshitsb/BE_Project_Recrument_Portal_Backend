"""Retell call registration for candidates."""
import re
from datetime import datetime, timezone

from fastapi import HTTPException

from config import settings
from database import get_database
from db.collections import (
    INTERVIEWS, INTERVIEWERS, INTERVIEW_RESPONSES,
)
from interview.candidate_schemas import RegisterCallResponse
from interview.candidate_service import _oid
from ai_services.interview_engine import generate_retell_agent_prompt
from retell_sdk import Retell

retell_client = Retell(api_key=settings.RETELL_API_KEY)


def _parse_duration(time_duration: str) -> int:
    """Extract minutes from '30 mins', '1 hour', etc."""
    match = re.search(r"\d+", time_duration)
    return int(match.group()) if match else 30


async def register_call(
    token: str, candidate_id: str, data,
) -> RegisterCallResponse:
    db = get_database()
    doc = await db[INTERVIEWS].find_one(
        {"interview_token": token})
    if not doc:
        raise HTTPException(404, "Interview not found")
    if doc["candidate_id"] != candidate_id:
        raise HTTPException(403, "Not authorized")
    if not doc["is_active"]:
        raise HTTPException(410, "Interview is no longer active")
    existing = await db[INTERVIEW_RESPONSES].find_one({
        "interview_id": str(doc["_id"]),
        "candidate_id": candidate_id,
        "is_ended": False,
    })
    if existing:
        raise HTTPException(
            400, "An interview session is already in progress")
    interviewer = await db[INTERVIEWERS].find_one(
        {"_id": _oid(doc["interviewer_id"])})
    if not interviewer:
        raise HTTPException(404, "Interviewer not found")
    agent_prompt = generate_retell_agent_prompt(
        name=doc["name"], objective=doc["objective"],
        questions=doc["questions"],
        duration_mins=_parse_duration(doc["time_duration"]),
        candidate_name=data.candidate_name)
    try:
        web_call = retell_client.call.create_web_call(
            agent_id=interviewer["agent_id"],
            retell_llm_dynamic_variables={
                "candidate_name": data.candidate_name,
                "objective": doc["objective"],
                "questions": agent_prompt,
                "mins": _parse_duration(doc["time_duration"]),
            })
    except Exception as e:
        raise HTTPException(
            502, f"Failed to register call with Retell: {e}")
    now = datetime.now(timezone.utc)
    await db[INTERVIEW_RESPONSES].insert_one({
        "interview_id": str(doc["_id"]),
        "candidate_id": candidate_id,
        "call_id": web_call.call_id,
        "name": data.candidate_name,
        "email": data.candidate_email,
        "duration": None, "details": None,
        "analytics": None, "candidate_status": "pending",
        "is_analysed": False, "is_ended": False,
        "is_viewed": False, "tab_switch_count": 0,
        "created_at": now, "updated_at": now,
    })
    await db[INTERVIEWS].update_one(
        {"_id": doc["_id"]},
        {"$inc": {"response_count": 1},
         "$set": {"updated_at": now}})
    return RegisterCallResponse(
        call_id=web_call.call_id,
        access_token=web_call.access_token,
        interview_id=str(doc["_id"]))
