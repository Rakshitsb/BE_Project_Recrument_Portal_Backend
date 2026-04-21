"""
Chatbot orchestration layer — candidate-facing business logic.

Responsibilities:
- Validate access guards (session is_enabled + application status)
- Delegate all DB operations to chatbot.session_service
- Call ai_services.rag_chatbot for AI responses

This module NEVER writes to MongoDB directly except for the read-only
application status guard check against db[APPLICATIONS].
"""

from fastapi import HTTPException, status

from ai_services.rag_chatbot import get_chatbot_response
from chatbot import session_service
from database import get_database
from db.collections import APPLICATIONS

_ELIGIBLE_STATUSES = {"shortlisted", "interview", "selected"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_candidate_sessions(candidate_id: str) -> list[dict]:
    """Return all chatbot sessions for the logged-in candidate (enabled and disabled).

    Args:
        candidate_id: The authenticated candidate's user id (string).

    Returns:
        List of ChatSessionSummary-compatible dicts, sorted by updated_at descending.
    """
    db = get_database()
    return await session_service.get_candidate_sessions(
        db, candidate_id, only_enabled=False
    )


async def get_session_detail(job_id: str, candidate_id: str) -> dict:
    """Return full chat session including all messages.

    Args:
        job_id:       String ObjectId of the job.
        candidate_id: The authenticated candidate's user id.

    Raises:
        HTTPException 404: Session does not exist.
        HTTPException 403: Chatbot is disabled for this job.

    Returns:
        ChatSessionDetail-compatible dict.
    """
    db = get_database()
    session = await session_service.get_session(db, job_id, candidate_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    if not session.get("is_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chatbot is not enabled for this job",
        )

    messages = await session_service.get_messages(db, job_id, candidate_id)

    return {
        "id": session["id"],
        "job_id": session["job_id"],
        "is_enabled": session["is_enabled"],
        "messages": messages,
        "updated_at": session.get("updated_at"),
    }


async def send_message(
    job_id: str,
    candidate_id: str,
    content: str,
) -> dict:
    """Process a candidate message through guards, RAG, and session persistence.

    Guard order (both must pass):
      1. Session exists AND is_enabled=True
      2. Application status in {shortlisted, interview, selected}

    Message flow:
      1. Fetch existing history BEFORE saving new message (clean context)
      2. Save user message
      3. Call RAG with prior history
      4. Save assistant message
      5. Return both messages

    Raises:
        HTTPException 403: Chatbot unavailable (not enabled or wrong status).
        HTTPException 404: Application not found.

    Returns:
        SendMessageResponse-compatible dict.
    """
    db = get_database()

    # GUARD 1 — session existence + enabled flag
    session = await session_service.get_session(db, job_id, candidate_id)
    if not session or not session.get("is_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chatbot is not available. You must be shortlisted for this job.",
        )

    # GUARD 2 — application status
    application = await db[APPLICATIONS].find_one(
        {"job_id": job_id, "candidate_id": candidate_id}
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    if application.get("status") not in _ELIGIBLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chatbot is only available for shortlisted candidates.",
        )

    # 1. Capture history BEFORE writing the new message to avoid duplication
    prior_history = await session_service.get_messages(db, job_id, candidate_id)

    # 2. Persist user message
    user_msg = await session_service.append_message(
        db, job_id, candidate_id, role="user", content=content
    )

    # 3. Call RAG engine with prior context only
    ai_text = await get_chatbot_response(
        db=db,
        job_id=job_id,
        candidate_id=candidate_id,
        user_message=content,
        chat_history=prior_history,
    )

    # 4. Persist AI reply
    assistant_msg = await session_service.append_message(
        db, job_id, candidate_id, role="assistant", content=ai_text
    )

    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
    }
