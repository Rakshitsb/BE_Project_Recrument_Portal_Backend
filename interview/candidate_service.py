"""Candidate interview list and detail operations."""
from bson import ObjectId
from fastapi import HTTPException

from database import get_database
from db.collections import INTERVIEWS, INTERVIEWERS
from interview.candidate_schemas import (
    CandidateInterviewerView,
    CandidateInterviewSummary,
    CandidateInterviewView,
)


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(400, "Invalid ID format")


async def get_my_interviews(
    candidate_id: str,
) -> list[CandidateInterviewSummary]:
    db = get_database()
    cursor = db[INTERVIEWS].find({
        "candidate_id": candidate_id,
        "is_active": True, "is_archived": False,
    }).sort("created_at", -1)
    results = []
    async for doc in cursor:
        results.append(CandidateInterviewSummary(
            id=str(doc["_id"]),
            name=doc["name"],
            description=doc["description"],
            time_duration=doc["time_duration"],
            question_count=doc["question_count"],
            is_active=doc["is_active"],
            created_at=doc["created_at"],
            interview_token=doc["interview_token"],
        ))
    return results


async def get_interview_by_token(
    token: str, candidate_id: str,
) -> CandidateInterviewView:
    db = get_database()
    doc = await db[INTERVIEWS].find_one(
        {"interview_token": token})
    if not doc:
        raise HTTPException(
            404, "Interview not found or link is invalid")
    if doc["candidate_id"] != candidate_id:
        raise HTTPException(
            403, "You are not authorized to access this interview")
    if not doc["is_active"]:
        raise HTTPException(
            410, "This interview link is no longer active")
    interviewer = await db[INTERVIEWERS].find_one(
        {"_id": _oid(doc["interviewer_id"])})
    if not interviewer:
        raise HTTPException(
            404, "Interviewer configuration not found")
    return CandidateInterviewView(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc["description"],
        interviewer=CandidateInterviewerView(
            id=str(interviewer["_id"]),
            name=interviewer["name"],
            description=interviewer["description"],
            image=interviewer["image"],
            audio=interviewer.get("audio"),
            empathy=interviewer["empathy"],
            exploration=interviewer["exploration"],
            rapport=interviewer["rapport"],
            speed=interviewer["speed"],
        ),
        time_duration=doc["time_duration"],
        question_count=doc["question_count"],
        is_active=doc["is_active"],
        created_at=doc["created_at"],
    )
