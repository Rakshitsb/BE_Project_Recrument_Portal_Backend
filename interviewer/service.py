from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from database import get_database
from db.collections import INTERVIEWERS
from interviewer.schemas import InterviewerCreate, InterviewerResponse


def _to_response(doc: dict) -> InterviewerResponse:
    return InterviewerResponse(
        id=str(doc["_id"]),
        agent_id=doc["agent_id"],
        name=doc["name"],
        description=doc["description"],
        image=doc["image"],
        audio=doc.get("audio"),
        empathy=doc["empathy"],
        exploration=doc["exploration"],
        rapport=doc["rapport"],
        speed=doc["speed"],
        created_at=doc["created_at"],
    )


def _object_id(interviewer_id: str) -> ObjectId:
    try:
        return ObjectId(interviewer_id)
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid interviewer ID format",
        )


async def get_all_interviewers() -> list[InterviewerResponse]:
    db = get_database()
    cursor = db[INTERVIEWERS].find().sort("created_at", 1)
    return [_to_response(doc) async for doc in cursor]


async def get_interviewer_by_id(
    interviewer_id: str,
) -> InterviewerResponse:
    db = get_database()
    doc = await db[INTERVIEWERS].find_one(
        {"_id": _object_id(interviewer_id)}
    )
    if not doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Interviewer not found"
        )
    return _to_response(doc)


async def create_interviewer(
    data: InterviewerCreate,
) -> InterviewerResponse:
    db = get_database()
    existing = await db[INTERVIEWERS].find_one(
        {"agent_id": data.agent_id}
    )
    if existing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Interviewer with this agent_id already exists",
        )
    doc = {
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db[INTERVIEWERS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def delete_interviewer(interviewer_id: str) -> dict:
    db = get_database()
    doc = await db[INTERVIEWERS].find_one(
        {"_id": _object_id(interviewer_id)}
    )
    if not doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Interviewer not found"
        )
    await db[INTERVIEWERS].delete_one({"_id": doc["_id"]})
    return {"message": "Interviewer deleted successfully"}
