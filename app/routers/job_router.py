from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.services.job_service import JobService
from app.schemas.job_schema import JobCreate, JobResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_job(job: JobCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only HR can create jobs"
        )

    job_id = await JobService.create_job(job, current_user["id"])
    return {"message": "Job created successfully", "jobId": job_id}


@router.get("/", response_model=List[JobResponse])
async def get_jobs(current_user: dict = Depends(get_current_user)):
    role = current_user["role"].lower()

    if role == "hr":
        jobs = await JobService.get_hr_jobs(current_user["id"])
    elif role == "user" or role == "candidate":
        jobs = await JobService.get_all_active_jobs()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role for viewing jobs",
        )

    return jobs
