"""Candidate-facing interview routes."""
from fastapi import APIRouter, Depends

from interview.candidate_schemas import (
    CandidateInterviewView, CandidateInterviewSummary,
    RegisterCallRequest, RegisterCallResponse,
)
from interview.candidate_service import (
    get_my_interviews, get_interview_by_token,
)
from interview.candidate_service_call import register_call
from middleware.auth_guard import require_candidate

router = APIRouter(
    prefix="/interviews/candidate", tags=["Interviews"],
)


@router.get(
    "/my", response_model=list[CandidateInterviewSummary],
)
async def my_interviews(
    current_user: dict = Depends(require_candidate),
) -> list[CandidateInterviewSummary]:
    return await get_my_interviews(current_user["id"])


@router.get(
    "/take/{token}",
    response_model=CandidateInterviewView,
)
async def take_interview(
    token: str,
    current_user: dict = Depends(require_candidate),
) -> CandidateInterviewView:
    return await get_interview_by_token(
        token, current_user["id"])


@router.post(
    "/take/{token}/register-call",
    response_model=RegisterCallResponse, status_code=201,
)
async def register(
    token: str, data: RegisterCallRequest,
    current_user: dict = Depends(require_candidate),
) -> RegisterCallResponse:
    return await register_call(
        token, current_user["id"], data)
