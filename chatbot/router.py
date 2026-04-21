"""Candidate and HR-facing chatbot routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from chatbot import hr_service, service
from chatbot.schemas import (
    ChatSessionDetail,
    ChatSessionSummary,
    ChatbotStatusResponse,
    HRSendMessageRequest,
    HRSendMessageResponse,
    HRSessionDetail,
    HRSessionListItem,
    SendMessageRequest,
    SendMessageResponse,
)
from database import get_database
from middleware.auth_guard import require_candidate, require_hr

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


def _candidate_id(current_user: dict) -> str:
    """Extract string candidate_id from the auth guard result."""
    return current_user["id"]


@router.get(
    "/sessions",
    response_model=list[ChatSessionSummary],
    summary="List all active chatbot sessions for the logged-in candidate",
)
async def list_sessions(
    current_user: dict = Depends(require_candidate),
) -> list[ChatSessionSummary]:
    """Return all chatbot sessions where is_enabled=True for the authenticated candidate."""
    candidate_id = _candidate_id(current_user)
    sessions = await service.list_candidate_sessions(candidate_id)
    return sessions


@router.get(
    "/sessions/{job_id}",
    response_model=ChatSessionDetail,
    summary="Get full chat history for a specific job's chatbot session",
)
async def get_session(
    job_id: str,
    current_user: dict = Depends(require_candidate),
) -> ChatSessionDetail:
    """Return the complete message history for a candidate's chatbot session on a job.

    Raises 404 if the session doesn't exist, 403 if the chatbot is disabled.
    """
    candidate_id = _candidate_id(current_user)
    detail = await service.get_session_detail(job_id, candidate_id)
    return detail


@router.post(
    "/sessions/{job_id}/message",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary=(
        "Send a message to the chatbot for a specific job. "
        "Requires candidate to be shortlisted and chatbot to be enabled."
    ),
)
async def send_message(
    job_id: str,
    body: SendMessageRequest,
    current_user: dict = Depends(require_candidate),
) -> SendMessageResponse:
    """Send a candidate message, trigger the RAG response, and return both messages.

    Both access guards are enforced:
    - Chatbot session must exist and have is_enabled=True
    - Candidate's application status must be shortlisted / interview / selected
    """
    candidate_id = _candidate_id(current_user)
    result = await service.send_message(
        job_id=job_id,
        candidate_id=candidate_id,
        content=body.content,
    )
    return result


# ---------------------------------------------------------------------------
# HR routes (added in Prompt 6)
# ---------------------------------------------------------------------------


@router.get(
    "/hr/sessions",
    response_model=list[HRSessionListItem],
    summary="List all chatbot sessions for this HR's jobs. Optionally filter by job_id.",
)
async def hr_list_sessions(
    job_id: Optional[str] = Query(default=None, description="Filter sessions by job ID"),
    current_user: dict = Depends(require_hr),
) -> list[HRSessionListItem]:
    """Return all chatbot sessions owned by the authenticated HR, optionally filtered by job."""
    db = get_database()
    hr_id = current_user["id"]
    return await hr_service.list_hr_sessions(db, hr_id, job_id)


@router.get(
    "/hr/sessions/{job_id}/{candidate_id}",
    response_model=HRSessionDetail,
    summary="Get full chat history for a specific candidate-job session (HR view)",
)
async def hr_get_session(
    job_id: str,
    candidate_id: str,
    current_user: dict = Depends(require_hr),
) -> HRSessionDetail:
    """Return the complete message history for a candidate-job session.

    Raises 403 if the session does not belong to the requesting HR.
    """
    db = get_database()
    hr_id = current_user["id"]
    return await hr_service.get_hr_session_detail(db, job_id, candidate_id, hr_id)


@router.post(
    "/hr/sessions/{job_id}/{candidate_id}/enable",
    response_model=ChatbotStatusResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Manually enable the chatbot for a candidate. "
        "Also triggered automatically when candidate is shortlisted."
    ),
)
async def hr_enable_chatbot(
    job_id: str,
    candidate_id: str,
    current_user: dict = Depends(require_hr),
) -> ChatbotStatusResponse:
    """Enable chatbot access for the specified candidate on this job."""
    db = get_database()
    hr_id = current_user["id"]
    return await hr_service.enable_chatbot(db, job_id, candidate_id, hr_id)


@router.post(
    "/hr/sessions/{job_id}/{candidate_id}/disable",
    response_model=ChatbotStatusResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Manually disable the chatbot for a candidate. "
        "Also triggered automatically when candidate is rejected."
    ),
)
async def hr_disable_chatbot(
    job_id: str,
    candidate_id: str,
    current_user: dict = Depends(require_hr),
) -> ChatbotStatusResponse:
    """Disable chatbot access for the specified candidate on this job."""
    db = get_database()
    hr_id = current_user["id"]
    return await hr_service.disable_chatbot(db, job_id, candidate_id, hr_id)


@router.post(
    "/hr/sessions/{job_id}/{candidate_id}/send-message",
    response_model=HRSendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a personalized HR message directly into a candidate's chat session.",
)
async def hr_send_message(
    job_id: str,
    candidate_id: str,
    body: HRSendMessageRequest,
    current_user: dict = Depends(require_hr),
) -> HRSendMessageResponse:
    """Send a personalized HR message directly into a candidate's chat session.

    Triggered from the 'Create Interview' screen via the 'Send to Personalized Chat' button.
    Supports optional interview_link and interview_id for deep-linking.
    The message appears as a special modal/banner in the candidate's chat UI.
    """
    db = get_database()
    hr_id = current_user["id"]
    return await hr_service.send_hr_message(
        db=db,
        job_id=job_id,
        candidate_id=candidate_id,
        hr_id=hr_id,
        message=body.message,
        interview_link=body.interview_link,
        interview_id=body.interview_id,
        message_type=body.message_type,
    )
