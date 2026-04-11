from fastapi import APIRouter, Depends, HTTPException

from interviewer.schemas import InterviewerCreate, InterviewerResponse
from interviewer.service import (
    create_interviewer,
    delete_interviewer,
    get_all_interviewers,
    get_interviewer_by_id,
)
from middleware.auth_guard import get_current_user, require_admin

router = APIRouter(prefix="/interviewers", tags=["Interviewers"])


def require_hr_or_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user["role"] not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return current_user


@router.get("/", response_model=list[InterviewerResponse])
async def list_all(
    _: dict = Depends(require_hr_or_admin),
) -> list[InterviewerResponse]:
    return await get_all_interviewers()


@router.get("/{interviewer_id}", response_model=InterviewerResponse)
async def get_one(
    interviewer_id: str,
    _: dict = Depends(require_hr_or_admin),
) -> InterviewerResponse:
    return await get_interviewer_by_id(interviewer_id)


@router.post(
    "/", response_model=InterviewerResponse, status_code=201
)
async def create(
    data: InterviewerCreate,
    _: dict = Depends(require_admin),
) -> InterviewerResponse:
    return await create_interviewer(data)


@router.delete("/{interviewer_id}", status_code=200)
async def delete(
    interviewer_id: str,
    _: dict = Depends(require_admin),
) -> dict:
    return await delete_interviewer(interviewer_id)
