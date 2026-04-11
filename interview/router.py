from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from middleware.auth_guard import require_hr, require_candidate
from interview.schemas import (
    InterviewCreate,
    InterviewUpdate,
    InterviewResponse,
    GenerateQuestionsRequest,
    ResponseRecord,
)
from interview.service import (
    create_interview,
    get_interviews_by_hr,
    get_interview_by_id,
    get_interview_by_slug,
    update_interview,
    delete_interview,
    get_responses_by_interview,
    get_candidate_interviews,
    create_response,
)


class RegisterCallRequest(BaseModel):
    interviewer_id: str


router = APIRouter(prefix="/interviews", tags=["Interviews"])


# ── Webhook Endpoint (no auth — Retell calls this) ───────────────────────────


@router.post("/webhook/retell", response_model=dict)
async def retell_webhook(request: Request) -> dict:
    body = await request.json()
    signature = request.headers.get("x-retell-signature", "")
    from interview.webhook_service import handle_retell_webhook
    return await handle_retell_webhook(body, signature)


# ── Candidate Endpoints ──────────────────────────────────────────────────────


@router.get("/my", response_model=list[InterviewResponse])
async def my_interviews(
    current_user: dict = Depends(require_candidate),
) -> list[InterviewResponse]:
    return await get_candidate_interviews(current_user["id"])


@router.get("/slug/{slug}", response_model=InterviewResponse)
async def interview_by_slug(slug: str) -> InterviewResponse:
    return await get_interview_by_slug(slug)


# ── HR Endpoints ─────────────────────────────────────────────────────────────


@router.post("/", response_model=InterviewResponse, status_code=201)
async def create(
    data: InterviewCreate,
    current_user: dict = Depends(require_hr),
) -> InterviewResponse:
    return await create_interview(current_user["id"], data)


@router.get("/", response_model=list[InterviewResponse])
async def list_interviews(
    current_user: dict = Depends(require_hr),
) -> list[InterviewResponse]:
    return await get_interviews_by_hr(current_user["id"])


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: str,
    current_user: dict = Depends(require_hr),
) -> InterviewResponse:
    return await get_interview_by_id(
        interview_id,
        current_user["id"],
        current_user["role"],
    )


@router.put("/{interview_id}", response_model=InterviewResponse)
async def edit_interview(
    interview_id: str,
    data: InterviewUpdate,
    current_user: dict = Depends(require_hr),
) -> InterviewResponse:
    return await update_interview(interview_id, current_user["id"], data)


@router.delete("/{interview_id}", response_model=dict)
async def remove_interview(
    interview_id: str,
    current_user: dict = Depends(require_hr),
) -> dict:
    return await delete_interview(interview_id, current_user["id"])


@router.get("/{interview_id}/responses", response_model=list[ResponseRecord])
async def interview_responses(
    interview_id: str,
    current_user: dict = Depends(require_hr),
) -> list[ResponseRecord]:
    return await get_responses_by_interview(
        interview_id,
        current_user["id"],
    )


@router.post("/{interview_id}/generate-questions", response_model=dict)
async def generate_interview_questions(
    interview_id: str,
    data: GenerateQuestionsRequest,
    current_user: dict = Depends(require_hr),
) -> dict:
    from ai_services.interview_questions import generate_questions
    result = await generate_questions(data)
    return result


# ── Candidate Call Registration ───────────────────────────────────────────────


@router.post("/{interview_id}/register-call", response_model=dict)
async def register_interview_call(
    interview_id: str,
    data: RegisterCallRequest,
    current_user: dict = Depends(require_candidate),
) -> dict:
    from interview.retell_service import register_call
    result = await register_call(
        interview_id,
        current_user["id"],
        data.interviewer_id,
    )
    return result
