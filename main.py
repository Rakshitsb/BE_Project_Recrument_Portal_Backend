from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin.router import router as admin_router
from ai.router import router as ai_router
from applications.router import router as applications_router
from auth.router import router as auth_router
from candidate.router import router as candidate_router
from database import get_database
from db.indexes import create_indexes
from hr.router import router as hr_router
from interviewer.router import router as interviewer_router
from interview.candidate_router import router as interview_candidate_router
from interview.router import router as interview_router
from interview_response.router import router as interview_response_router
from jobs.router import router as jobs_router
from retell.router import router as retell_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_database()
    await create_indexes(db)
    yield


app = FastAPI(
    title="AI-Powered HR Recruitment Portal",
    version="2.0.0",
    description="Backend API for managing candidates, HR profiles, job postings, applications and AI interviews.",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router)
app.include_router(candidate_router)
app.include_router(hr_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(admin_router)
app.include_router(ai_router)
app.include_router(interviewer_router)
app.include_router(interview_router)
app.include_router(interview_candidate_router)
app.include_router(interview_response_router)
app.include_router(retell_router)


@app.get("/", tags=["Health"])
async def root() -> dict:
    return {"message": "HR Recruitment Portal API is running"}


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "version": "2.0.0", "modules": ["auth", "candidate", "hr", "jobs", "applications", "admin", "ai", "interviewer", "interview", "interview_response", "retell"]}
