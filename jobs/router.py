from fastapi import APIRouter, Depends

from jobs.schemas import JobCreate, JobUpdate, JobResponse
from jobs.service import create_job, get_all_jobs, get_job_by_id, update_job, delete_job
from middleware.auth_guard import require_hr

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=201)
async def create(
    data: JobCreate,
    current_user: dict = Depends(require_hr),
) -> JobResponse:
    return await create_job(current_user["id"], data)


@router.get("/", response_model=list[JobResponse])
async def list_all() -> list[JobResponse]:
    return await get_all_jobs()


@router.get("/{job_id}", response_model=JobResponse)
async def get_one(job_id: str) -> JobResponse:
    return await get_job_by_id(job_id)


@router.put("/{job_id}", response_model=JobResponse)
async def update(
    job_id: str,
    data: JobUpdate,
    current_user: dict = Depends(require_hr),
) -> JobResponse:
    return await update_job(job_id, current_user["id"], data)


@router.delete("/{job_id}", status_code=200)
async def delete(
    job_id: str,
    current_user: dict = Depends(require_hr),
) -> dict:
    return await delete_job(job_id, current_user["id"])
