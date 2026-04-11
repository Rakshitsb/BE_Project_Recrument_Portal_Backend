from fastapi import APIRouter, Depends

from interviewer.schemas import InterviewerResponse
from interviewer.service import (
    setup_interviewers,
    get_all_interviewers,
    get_interviewer_by_id,
)
from middleware.auth_guard import require_hr

router = APIRouter(prefix="/interviewers", tags=["Interviewers"])


@router.post("/setup", response_model=list[InterviewerResponse], status_code=201)
async def setup(
    current_user: dict = Depends(require_hr),
) -> list[InterviewerResponse]:
    return await setup_interviewers()


@router.get("/", response_model=list[InterviewerResponse])
async def list_interviewers(
    current_user: dict = Depends(require_hr),
) -> list[InterviewerResponse]:
    return await get_all_interviewers()


@router.get("/{interviewer_id}", response_model=InterviewerResponse)
async def get_interviewer(
    interviewer_id: str,
    current_user: dict = Depends(require_hr),
) -> InterviewerResponse:
    return await get_interviewer_by_id(interviewer_id)
