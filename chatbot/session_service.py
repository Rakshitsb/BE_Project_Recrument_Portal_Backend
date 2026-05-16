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

from db.collections import CANDIDATE_PROFILES, CHATBOT_SESSIONS, JOBS, HR_PROFILES

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
        List of dicts: ``{id, job_id, job_title, is_enabled, enabled_at, message_count, updated_at}``.
    """
    from bson import ObjectId
    from bson.errors import InvalidId

    query: dict = {"candidate_id": candidate_id}
    if only_enabled:
        query["is_enabled"] = True

    cursor = db[CHATBOT_SESSIONS].find(
        query,
        {"_id": 1, "job_id": 1, "is_enabled": 1, "enabled_at": 1, "updated_at": 1, "messages": 1},
    ).sort("updated_at", DESCENDING)

    raw_sessions: list[dict] = []
    async for doc in cursor:
        raw_sessions.append({
            "id": str(doc["_id"]),
            "job_id": doc.get("job_id", ""),
            "is_enabled": doc.get("is_enabled", False),
            "enabled_at": doc.get("enabled_at"),
            "message_count": len(doc.get("messages", [])),
            "updated_at": doc.get("updated_at"),
        })

    if not raw_sessions:
        return []

    # ── Batch-enrich with job titles ─────────────────────────────────────────
    job_ids = list({s["job_id"] for s in raw_sessions if s["job_id"]})
    job_title_map: dict[str, str] = {}
    job_company_map: dict[str, dict] = {}
    valid_oids: list[ObjectId] = []
    for jid in job_ids:
        try:
            valid_oids.append(ObjectId(jid))
        except (InvalidId, TypeError):
            pass

    if valid_oids:
        hr_ids = []
        async for jdoc in db[JOBS].find({"_id": {"$in": valid_oids}}, {"_id": 1, "title": 1, "hr_id": 1}):
            job_title_map[str(jdoc["_id"])] = jdoc.get("title", "")
            job_company_map[str(jdoc["_id"])] = {"hr_id": jdoc.get("hr_id")}
            if jdoc.get("hr_id"):
                hr_ids.append(jdoc.get("hr_id"))
        hr_profiles = {}
        if hr_ids:
            async for hdoc in db[HR_PROFILES].find({"user_id": {"$in": list(set(hr_ids))}}):
                hr_profiles[hdoc["user_id"]] = hdoc
        for jid, info in job_company_map.items():
            profile = hr_profiles.get(info.get("hr_id"), {})
            info["company_name"] = profile.get("company_name")
            info["company_logo_url"] = profile.get("avatar_url") or profile.get("profile_image", {}).get("url")

    results: list[dict] = []
    for item in raw_sessions:
        item["job_title"] = job_title_map.get(item["job_id"], "")
        item.update(job_company_map.get(item["job_id"], {}))
        results.append(item)
    return results



async def get_hr_sessions(
    db: Any, hr_id: str, job_id: str | None = None
) -> list[dict]:
    """List all chatbot sessions belonging to an HR user (optionally filtered by job).

    Returns:
        List of dicts: ``{id, job_id, candidate_id, is_enabled, message_count,
                          updated_at, candidate_name, job_title}``.
    """
    from bson import ObjectId
    from bson.errors import InvalidId

    query: dict = {"hr_id": hr_id}
    if job_id:
        query["job_id"] = job_id

    cursor = db[CHATBOT_SESSIONS].find(
        query,
        {"_id": 1, "job_id": 1, "candidate_id": 1, "is_enabled": 1, "updated_at": 1, "messages": 1},
    ).sort("updated_at", DESCENDING)

    raw_sessions: list[dict] = []
    async for doc in cursor:
        raw_sessions.append({
            "id": str(doc["_id"]),
            "job_id": doc.get("job_id", ""),
            "candidate_id": doc.get("candidate_id", ""),
            "is_enabled": doc.get("is_enabled", False),
            "message_count": len(doc.get("messages", [])),
            "updated_at": doc.get("updated_at"),
        })

    if not raw_sessions:
        return []

    # ── Batch-enrich with candidate names and job titles ──────────────────────

    candidate_ids = list({s["candidate_id"] for s in raw_sessions if s["candidate_id"]})
    job_ids = list({s["job_id"] for s in raw_sessions if s["job_id"]})

    # Fetch candidate full_name keyed by user_id
    candidate_name_map: dict[str, str] = {}
    candidate_avatar_map: dict[str, str] = {}
    async for cdoc in db[CANDIDATE_PROFILES].find(
        {"user_id": {"$in": candidate_ids}},
        {"user_id": 1, "full_name": 1, "avatar_url": 1, "profile_image": 1},
    ):
        candidate_name_map[cdoc["user_id"]] = cdoc.get("full_name", "")
        candidate_avatar_map[cdoc["user_id"]] = cdoc.get("avatar_url") or cdoc.get("profile_image", {}).get("url")

    # Fetch job title keyed by string _id
    job_title_map: dict[str, str] = {}
    valid_oids: list[ObjectId] = []
    for jid in job_ids:
        try:
            valid_oids.append(ObjectId(jid))
        except (InvalidId, TypeError):
            pass

    if valid_oids:
        async for jdoc in db[JOBS].find(
            {"_id": {"$in": valid_oids}},
            {"_id": 1, "title": 1},
        ):
            job_title_map[str(jdoc["_id"])] = jdoc.get("title", "")

    # Merge names/titles into result items
    results: list[dict] = []
    for item in raw_sessions:
        item["candidate_name"] = candidate_name_map.get(item["candidate_id"], "")
        item["candidate_avatar_url"] = candidate_avatar_map.get(item["candidate_id"], "")
        item["job_title"] = job_title_map.get(item["job_id"], "")
        results.append(item)

    return results



async def get_messages(db: Any, job_id: str, candidate_id: str) -> list[dict]:
    """Return the full messages array for a session, or ``[]`` if not found."""
    doc = await db[CHATBOT_SESSIONS].find_one(
        {"job_id": job_id, "candidate_id": candidate_id},
        {"messages": 1},
    )
    return doc.get("messages", []) if doc else []
