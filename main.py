from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.router import router as auth_router
from candidate.router import router as candidate_router
from hr.router import router as hr_router
from jobs.router import router as jobs_router
from applications.router import router as applications_router
from admin.router import router as admin_router
from ai.router import router as ai_router

app = FastAPI(
    title="AI-Powered HR Recruitment Portal",
    version="1.0.0",
    description="Backend API for managing candidates, HR profiles, job postings, and applications.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "https://localhost:5173"
                  ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(candidate_router)
app.include_router(hr_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(admin_router)
app.include_router(ai_router)


@app.get("/", tags=["Health"])
async def root() -> dict:
    return {"message": "HR Recruitment Portal API is running"}
