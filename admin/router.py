from fastapi import APIRouter, Depends

from admin.service import (
    get_all_candidates,
    get_all_hrs,
    get_all_jobs,
    get_all_applications,
    delete_candidate,
    delete_hr,
)
from middleware.auth_guard import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/candidates")
async def list_candidates(current_user: dict = Depends(require_admin)) -> list[dict]:
    return await get_all_candidates()


@router.get("/hrs")
async def list_hrs(current_user: dict = Depends(require_admin)) -> list[dict]:
    return await get_all_hrs()


@router.get("/jobs")
async def list_jobs(current_user: dict = Depends(require_admin)) -> list[dict]:
    return await get_all_jobs()


@router.get("/applications")
async def list_applications(current_user: dict = Depends(require_admin)) -> list[dict]:
    return await get_all_applications()


@router.delete("/candidate/{user_id}", status_code=200)
async def remove_candidate(
    user_id: str,
    current_user: dict = Depends(require_admin),
) -> dict:
    return await delete_candidate(user_id)


@router.delete("/hr/{user_id}", status_code=200)
async def remove_hr(
    user_id: str,
    current_user: dict = Depends(require_admin),
) -> dict:
    return await delete_hr(user_id)
