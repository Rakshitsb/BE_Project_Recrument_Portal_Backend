"""HR-facing interview routes."""
from fastapi import APIRouter, Depends

from interview.schemas import (
    InterviewCreate, InterviewResponse,
    InterviewSummary, InterviewUpdate,
)
from interview.service import create_interview
from interview.service_update import (
    delete_interview, get_interview_by_id,
    list_interviews_by_hr, update_interview,
)
from middleware.auth_guard import require_hr

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post(
    "/", response_model=InterviewResponse, status_code=201,
)
async def create(
    data: InterviewCreate,
    current_user: dict = Depends(require_hr),
) -> InterviewResponse:
    return await create_interview(current_user["id"], data)


@router.get("/", response_model=list[InterviewSummary])
async def list_all(
    current_user: dict = Depends(require_hr),
) -> list[InterviewSummary]:
    return await list_interviews_by_hr(current_user["id"])


@router.get(
    "/{interview_id}", response_model=InterviewResponse,
)
async def get_one(
    interview_id: str,
    current_user: dict = Depends(require_hr),
) -> InterviewResponse:
    return await get_interview_by_id(
        interview_id, current_user["id"])


@router.patch(
    "/{interview_id}", response_model=InterviewResponse,
)
async def update(
    interview_id: str, data: InterviewUpdate,
    current_user: dict = Depends(require_hr),
) -> InterviewResponse:
    return await update_interview(
        interview_id, current_user["id"], data)


@router.delete("/{interview_id}", status_code=200)
async def delete(
    interview_id: str,
    current_user: dict = Depends(require_hr),
) -> dict:
    return await delete_interview(
        interview_id, current_user["id"])
