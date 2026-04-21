"""
DB layer for chatbot sessions.

All business logic (enable/disable hooks, RAG calls) lives in chatbot/service.py.
This module only handles MongoDB CRUD for the chatbot_sessions collection.

Collection: chatbot_sessions
Schema:
  _id          : ObjectId
  job_id       : str   — MongoDB ObjectId as string (ref → jobs)
  candidate_id : str   — MongoDB ObjectId as string (ref → users)
  hr_id        : str   — MongoDB ObjectId as string (owner HR of the job)
  is_enabled   : bool  — True = candidate can chat
  enabled_at   : datetime | None
  disabled_at  : datetime | None
  messages     : list[dict]  — append-only chat log
  created_at   : datetime
  updated_at   : datetime
"""

from datetime import datetime, timezone
from typing import Any

from nanoid import generate
from pymongo import DESCENDING, ReturnDocument

from db.collections import CHATBOT_SESSIONS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_session(doc: dict) -> dict:
    """Convert MongoDB document to API-safe dict (ObjectId → str, add message_count)."""
    if not doc:
        return {}
    doc["id"] = str(doc.pop("_id"))
    doc["message_count"] = len(doc.get("messages", []))
    return doc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_or_create_session(
    db: Any, job_id: str, candidate_id: str, hr_id: str
) -> dict:
    """Return existing session or atomically create one (upsert, race-safe).

    Args:
        db:           Motor async database instance.
        job_id:       String ObjectId of the job.
        candidate_id: String ObjectId of the candidate user.
        hr_id:        String ObjectId of the HR who owns the job.

    Returns:
        Serialized session document dict (includes ``id``, ``message_count``).
    """
    now = _now()
    doc = await db[CHATBOT_SESSIONS].find_one_and_update(
        {"job_id": job_id, "candidate_id": candidate_id},
        {
            "$setOnInsert": {
                "job_id": job_id,
                "candidate_id": candidate_id,
                "hr_id": hr_id,
                "is_enabled": False,
                "enabled_at": None,
                "disabled_at": None,
                "messages": [],
                "created_at": now,
                "updated_at": now,
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _serialize_session(doc)


async def get_session(db: Any, job_id: str, candidate_id: str) -> dict | None:
    """Find a session by job_id + candidate_id composite key."""
    doc = await db[CHATBOT_SESSIONS].find_one(
        {"job_id": job_id, "candidate_id": candidate_id}
    )
    return _serialize_session(doc) if doc else None


async def get_session_by_id(db: Any, session_id: str) -> dict | None:
    """Find a session by its MongoDB ObjectId string."""
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        oid = ObjectId(session_id)
    except (InvalidId, TypeError):
        return None
    doc = await db[CHATBOT_SESSIONS].find_one({"_id": oid})
    return _serialize_session(doc) if doc else None


async def append_message(
    db: Any,
    job_id: str,
    candidate_id: str,
    role: str,
    content: str,
    extra_fields: dict | None = None,
) -> dict:
    """Append a message to the session's messages array.

    Args:
        role:         ``"user"`` | ``"assistant"`` | ``"hr"``
        extra_fields: Optional extra keys merged into the message dict
                      (e.g. ``{"modal_payload": {...}}`` for HR messages).

    Returns:
        The newly appended message dict.
    """
    message: dict = {
        "id": generate(size=12),
        "role": role,
        "content": content,
        "timestamp": _now(),
        **(extra_fields or {}),
    }
    await db[CHATBOT_SESSIONS].update_one(
        {"job_id": job_id, "candidate_id": candidate_id},
        {"$push": {"messages": message}, "$set": {"updated_at": _now()}},
    )
    return message


async def set_enabled(
    db: Any,
    job_id: str,
    candidate_id: str,
    enabled: bool,
    hr_id: str | None = None,
) -> dict | None:
    """Enable or disable a candidate's chatbot session for a specific job.

    Args:
        enabled: ``True`` to enable (sets ``enabled_at``), ``False`` to disable.
        hr_id:   When provided, also writes ``hr_id`` on the document
                 (useful if session was created before hr_id was known).

    Returns:
        Updated serialized session dict, or ``None`` if session not found.
    """
    now = _now()
    update: dict
    if enabled:
        update = {"$set": {"is_enabled": True, "enabled_at": now, "disabled_at": None}}
    else:
        update = {"$set": {"is_enabled": False, "disabled_at": now, "enabled_at": None}}

    if hr_id:
        update["$set"]["hr_id"] = hr_id

    doc = await db[CHATBOT_SESSIONS].find_one_and_update(
        {"job_id": job_id, "candidate_id": candidate_id},
        update,
        return_document=ReturnDocument.AFTER,
    )
    return _serialize_session(doc) if doc else None


async def get_candidate_sessions(
    db: Any, candidate_id: str, only_enabled: bool = True
) -> list[dict]:
    """List sessions for a candidate with lightweight projection (no messages array).

    Args:
        only_enabled: When ``True``, only return sessions where ``is_enabled=True``.

    Returns:
        List of dicts: ``{id, job_id, is_enabled, enabled_at, message_count, updated_at}``.
    """
    query: dict = {"candidate_id": candidate_id}
    if only_enabled:
        query["is_enabled"] = True

    cursor = db[CHATBOT_SESSIONS].find(
        query,
        {"_id": 1, "job_id": 1, "is_enabled": 1, "enabled_at": 1, "updated_at": 1, "messages": 1},
    ).sort("updated_at", DESCENDING)

    results: list[dict] = []
    async for doc in cursor:
        item = {
            "id": str(doc["_id"]),
            "job_id": doc.get("job_id", ""),
            "is_enabled": doc.get("is_enabled", False),
            "enabled_at": doc.get("enabled_at"),
            "message_count": len(doc.get("messages", [])),
            "updated_at": doc.get("updated_at"),
        }
        results.append(item)
    return results


async def get_hr_sessions(
    db: Any, hr_id: str, job_id: str | None = None
) -> list[dict]:
    """List all chatbot sessions belonging to an HR user (optionally filtered by job).

    Returns:
        List of dicts: ``{id, job_id, candidate_id, is_enabled, message_count, updated_at}``.
    """
    query: dict = {"hr_id": hr_id}
    if job_id:
        query["job_id"] = job_id

    cursor = db[CHATBOT_SESSIONS].find(
        query,
        {"_id": 1, "job_id": 1, "candidate_id": 1, "is_enabled": 1, "updated_at": 1, "messages": 1},
    ).sort("updated_at", DESCENDING)

    results: list[dict] = []
    async for doc in cursor:
        item = {
            "id": str(doc["_id"]),
            "job_id": doc.get("job_id", ""),
            "candidate_id": doc.get("candidate_id", ""),
            "is_enabled": doc.get("is_enabled", False),
            "message_count": len(doc.get("messages", [])),
            "updated_at": doc.get("updated_at"),
        }
        results.append(item)
    return results


async def get_messages(db: Any, job_id: str, candidate_id: str) -> list[dict]:
    """Return the full messages array for a session, or ``[]`` if not found."""
    doc = await db[CHATBOT_SESSIONS].find_one(
        {"job_id": job_id, "candidate_id": candidate_id},
        {"messages": 1},
    )
    return doc.get("messages", []) if doc else []
