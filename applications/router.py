from fastapi import APIRouter, Depends

from applications.schemas import ApplicationCreate, ApplicationStatusUpdate, ApplicationResponse
from applications.service import (
    create_application,
    get_my_applications,
    get_job_applications,
    update_application_status,
    withdraw_application,
)
from middleware.auth_guard import require_candidate, require_hr

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/", response_model=ApplicationResponse, status_code=201)
async def apply(
    data: ApplicationCreate,
    current_user: dict = Depends(require_candidate),
) -> ApplicationResponse:
    return await create_application(current_user["id"], data)


@router.get("/my", response_model=list[ApplicationResponse])
async def my_applications(
    current_user: dict = Depends(require_candidate),
) -> list[ApplicationResponse]:
    return await get_my_applications(current_user["id"])


@router.get("/job/{job_id}", response_model=list[ApplicationResponse])
async def job_applications(
    job_id: str,
    current_user: dict = Depends(require_hr),
) -> list[ApplicationResponse]:
    return await get_job_applications(job_id, current_user["id"])


@router.put("/{app_id}/status", response_model=ApplicationResponse)
async def update_status(
    app_id: str,
    data: ApplicationStatusUpdate,
    current_user: dict = Depends(require_hr),
) -> ApplicationResponse:
    return await update_application_status(app_id, current_user["id"], data)


@router.delete("/{app_id}", status_code=200)
async def withdraw(
    app_id: str,
    current_user: dict = Depends(require_candidate),
) -> dict:
    return await withdraw_application(app_id, current_user["id"])
