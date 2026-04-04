from datetime import datetime, timezone

from fastapi import HTTPException, status

from database import get_database
from candidate.schemas import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    CandidateProfileResponse,
)

COLLECTION = "candidate_profiles"


def _to_response(doc: dict) -> CandidateProfileResponse:
    return CandidateProfileResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        created_at=doc["created_at"],
        **{k: doc[k] for k in CandidateProfileCreate.model_fields},
    )


async def create_profile(user_id: str, data: CandidateProfileCreate) -> CandidateProfileResponse:
    db = get_database()
    col = db[COLLECTION]

    if await col.find_one({"user_id": user_id}):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Profile already exists")

    doc = {"user_id": user_id, "created_at": datetime.now(timezone.utc), **data.model_dump()}
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def get_profile(user_id: str) -> CandidateProfileResponse:
    db = get_database()
    doc = await db[COLLECTION].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return _to_response(doc)


async def update_profile(user_id: str, data: CandidateProfileUpdate) -> CandidateProfileResponse:
    db = get_database()
    col = db[COLLECTION]

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return await get_profile(user_id)

    result = await col.find_one_and_update(
        {"user_id": user_id},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return _to_response(result)


async def delete_profile(user_id: str) -> dict:
    db = get_database()
    result = await db[COLLECTION].find_one_and_delete({"user_id": user_id})
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return {"message": "Profile deleted successfully"}
