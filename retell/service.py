from datetime import datetime, timezone

from config import settings
from database import get_database
from db.collections import INTERVIEW_RESPONSES
from retell.logging import logger
from retell.schemas import RetellCallPayload
from retell_sdk import Retell

retell_client = Retell(api_key=settings.RETELL_API_KEY)


async def handle_call_started(call: RetellCallPayload) -> None:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one({"call_id": call.call_id})
    if not doc:
        logger.warning("No response doc for call %s", call.call_id)
        return
    if doc.get("call_status") == "started":
        return
    await db[INTERVIEW_RESPONSES].update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "call_status": "started",
            "updated_at": datetime.now(timezone.utc),
        }},
    )


async def handle_call_ended(call: RetellCallPayload) -> None:
    db = get_database()
    doc = await db[INTERVIEW_RESPONSES].find_one({"call_id": call.call_id})
    if not doc:
        logger.warning("No response doc for call %s", call.call_id)
        return
    if doc.get("is_ended") is True:
        return
    duration = 0
    if call.start_timestamp and call.end_timestamp:
        duration = round((call.end_timestamp - call.start_timestamp) / 1000)
    await db[INTERVIEW_RESPONSES].update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "is_ended": True,
            "duration": duration,
            "updated_at": datetime.now(timezone.utc),
        }},
    )


def verify_retell_signature(raw_body: bytes, signature: str) -> bool:
    return Retell.verify(
        body=raw_body,
        api_key=settings.RETELL_API_KEY,
        signature=signature,
    )
