"""
HR-side chatbot orchestration — enable/disable controls and session inspection.

Split into this file to keep chatbot/service.py under 150 lines.
All candidate-facing logic remains in chatbot/service.py.

The handle_application_status_hook() function is the auto-trigger entry point
called from applications/service.py after a status update succeeds.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from chatbot import session_service

logger = logging.getLogger(__name__)


async def enable_chatbot(
    db: Any, job_id: str, candidate_id: str, hr_id: str
) -> dict:
    """Enable the chatbot session for a candidate on a specific job.

    Creates the session atomically if it doesn't exist yet, then enables it.

    Args:
        db:           Motor async database instance.
        job_id:       String ObjectId of the job.
        candidate_id: String ObjectId of the candidate user.
        hr_id:        String ObjectId of the HR performing the action.

    Raises:
        HTTPException 404: Session could not be created or found.

    Returns:
        ChatbotStatusResponse-compatible dict.
    """
    # Ensure the session document exists before enabling
    await session_service.get_or_create_session(db, job_id, candidate_id, hr_id)

    result = await session_service.set_enabled(
        db, job_id, candidate_id, enabled=True, hr_id=hr_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return _to_status_response(result)


async def disable_chatbot(
    db: Any, job_id: str, candidate_id: str, hr_id: str
) -> dict:
    """Disable the chatbot session for a candidate on a specific job.

    Args:
        db:           Motor async database instance.
        job_id:       String ObjectId of the job.
        candidate_id: String ObjectId of the candidate user.
        hr_id:        Unused here but kept for consistent signature with enable_chatbot.

    Raises:
        HTTPException 404: Session not found.

    Returns:
        ChatbotStatusResponse-compatible dict.
    """
    result = await session_service.set_enabled(
        db, job_id, candidate_id, enabled=False
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    return _to_status_response(result)


async def list_hr_sessions(
    db: Any, hr_id: str, job_id: str | None = None
) -> list[dict]:
    """Return all chatbot sessions belonging to this HR, optionally filtered by job.

    Returns:
        List of HRSessionListItem-compatible dicts.
    """
    return await session_service.get_hr_sessions(db, hr_id, job_id)


async def get_hr_session_detail(
    db: Any, job_id: str, candidate_id: str, hr_id: str
) -> dict:
    """Return the full message history for a candidate-job session (HR view).

    Enforces that the requesting HR owns the session.

    Raises:
        HTTPException 404: Session not found.
        HTTPException 403: HR does not own this session.

    Returns:
        HRSessionDetail-compatible dict.
    """
    session = await session_service.get_session(db, job_id, candidate_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    if session.get("hr_id") != hr_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    messages = await session_service.get_messages(db, job_id, candidate_id)

    return {
        "id": session["id"],
        "job_id": session.get("job_id", job_id),
        "candidate_id": session.get("candidate_id", candidate_id),
        "is_enabled": session.get("is_enabled", False),
        "messages": messages,
        "enabled_at": session.get("enabled_at"),
        "disabled_at": session.get("disabled_at"),
        "updated_at": session.get("updated_at"),
    }


async def handle_application_status_hook(
    db: Any,
    job_id: str,
    candidate_id: str,
    hr_id: str,
    new_status: str,
) -> None:
    """Auto-trigger chatbot enable/disable based on application status changes.

    # Non-blocking hook — chatbot failure must not affect core flow.
    Called from applications/service.py after a successful status update.
    The caller wraps this in try/except so any exception here is swallowed.

    Args:
        new_status: The new application status string.
                    "shortlisted" → enable; "rejected" → disable; others → no-op.
    """
    try:
        if new_status == "shortlisted":
            await enable_chatbot(db, job_id, candidate_id, hr_id)
        elif new_status == "rejected":
            await disable_chatbot(db, job_id, candidate_id, hr_id)
        # All other statuses: no chatbot action
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[ChatbotHook] Non-fatal hook error for job=%s candidate=%s: %s",
            job_id, candidate_id, exc,
        )


async def send_hr_message(
    db: Any,
    job_id: str,
    candidate_id: str,
    hr_id: str,
    message: str,
    interview_link: str | None = None,
    interview_id: str | None = None,
    message_type: str = "general",
) -> dict:
    """Inject a personalized HR message into a candidate's chat session.

    Triggered from the 'Send to Personalized Chat' button on the Create Interview screen.
    The message is stored with role='hr' and a structured modal_payload dict that the
    frontend uses to render the message as a special banner or interview invite card.

    Guards (all three must pass):
      1. Session must exist
      2. Session hr_id must match the requesting HR
      3. Session must be enabled

    Args:
        message:        The HR's message text (max 2000 chars).
        interview_link: Optional URL for the interview (e.g. Retell or Meet link).
        interview_id:   Optional ObjectId string of the related interview document.
        message_type:   ``"general"`` or ``"interview_invite"`` — used by frontend to
                        decide the rendering style.

    Returns:
        HRSendMessageResponse-compatible dict.
    """
    # GUARD 1 — session must exist
    session = await session_service.get_session(db, job_id, candidate_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found. The candidate may not have been shortlisted yet.",
        )

    # GUARD 2 — HR ownership
    if session.get("hr_id") != hr_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only message candidates on your own jobs.",
        )

    # GUARD 3 — session must be enabled
    if not session.get("is_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chatbot session is disabled for this candidate. Enable it before sending a message.",
        )

    # Build modal_payload — always a dict, never None
    modal_payload: dict = {
        "type": message_type,
        "interview_link": interview_link,
        "interview_id": interview_id,
        "sent_by_hr_id": hr_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist HR message with embedded payload
    hr_msg = await session_service.append_message(
        db,
        job_id,
        candidate_id,
        role="hr",
        content=message,
        extra_fields={"modal_payload": modal_payload},
    )

    return {
        "hr_message": hr_msg,
        "session_id": str(session["id"]),
        "candidate_id": candidate_id,
        "job_id": job_id,
    }


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------


def _to_status_response(session: dict) -> dict:
    """Convert a serialized session dict into a ChatbotStatusResponse-compatible dict."""
    return {
        "job_id": session.get("job_id", ""),
        "candidate_id": session.get("candidate_id", ""),
        "is_enabled": session.get("is_enabled", False),
        "enabled_at": session.get("enabled_at"),
        "disabled_at": session.get("disabled_at"),
        "message_count": session.get("message_count", 0),
        "updated_at": session.get("updated_at"),
    }
