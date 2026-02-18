from app.db.database import async_job_collection
from app.schemas.job_schema import JobCreate
from datetime import datetime
from bson import ObjectId


class JobService:
    @staticmethod
    async def create_job(job_data: JobCreate, user_id: str) -> str:
        new_job = job_data.model_dump()
        new_job["createdBy"] = user_id
        new_job["createdAt"] = datetime.utcnow()
        new_job["isActive"] = True

        result = await async_job_collection.insert_one(new_job)
        return str(result.inserted_id)

    @staticmethod
    async def get_hr_jobs(user_id: str):
        jobs_cursor = async_job_collection.find({"createdBy": user_id})
        jobs = await jobs_cursor.to_list(length=None)

        # Convert ObjectId to string for Pydantic
        for job in jobs:
            job["_id"] = str(job["_id"])

        return jobs

    @staticmethod
    async def get_all_active_jobs():
        jobs_cursor = async_job_collection.find({"isActive": True})
        jobs = await jobs_cursor.to_list(length=None)

        for job in jobs:
            job["_id"] = str(job["_id"])

        return jobs
