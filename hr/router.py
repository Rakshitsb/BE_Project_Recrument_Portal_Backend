from fastapi import APIRouter, Depends

from hr.schemas import (
    HRDashboardResponse,
    HRProfileCreate,
    HRProfileResponse,
    HRProfileUpdate,
)
from hr.service import create_profile, delete_profile, get_dashboard, get_profile, update_profile
from middleware.auth_guard import require_hr

router = APIRouter(prefix="/hr", tags=["HR"])


@router.get("/dashboard", response_model=HRDashboardResponse)
async def dashboard(
    current_user: dict = Depends(require_hr),
) -> HRDashboardResponse:
    return await get_dashboard(current_user["id"])


@router.post("/profile", response_model=HRProfileResponse, status_code=201)
async def create(
    data: HRProfileCreate,
    current_user: dict = Depends(require_hr),
) -> HRProfileResponse:
    return await create_profile(current_user["id"], data)


@router.get("/profile", response_model=HRProfileResponse)
async def get(
    current_user: dict = Depends(require_hr),
) -> HRProfileResponse:
    return await get_profile(current_user["id"])


@router.put("/profile", response_model=HRProfileResponse)
async def update(
    data: HRProfileUpdate,
    current_user: dict = Depends(require_hr),
) -> HRProfileResponse:
    return await update_profile(current_user["id"], data)


@router.delete("/profile", status_code=200)
async def delete(
    current_user: dict = Depends(require_hr),
) -> dict:
    return await delete_profile(current_user["id"])
