"""
HR Recruitment Portal — Backend API
Version: 2.1.0

New in 2.1.0:
  - AI JD Parser (POST /ai/parse-jd)
  - RAG Chatbot for shortlisted candidates (POST /chatbot/sessions/{job_id}/message)
  - HR Chatbot Controls (POST /chatbot/hr/sessions/{job_id}/{candidate_id}/enable|disable)
  - HR Personalized Message API (POST /chatbot/hr/sessions/{job_id}/{candidate_id}/send-message)
  - SBERT Skill Matcher scaffold (POST /ai/match-job)
  - ChromaDB in-memory vector store rebuilt from MongoDB on every startup
"""
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
from chatbot.router import router as chatbot_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_database()
    await create_indexes(db)

    # Rebuild ChromaDB in-memory vector index from MongoDB on every startup.
    # MongoDB (Atlas) is the source of truth — embeddings survive redeploys.
    # ChromaDB is ephemeral in-memory only; this rebuild takes ~1–3s.
    try:
        from ai_services.vector_store import build_chroma_collection
        await build_chroma_collection(db)
        print("[Startup] ChromaDB in-memory index rebuilt successfully.")
    except Exception as e:
        # Non-fatal — server starts even if vector store rebuild fails.
        # RAG chatbot will fall back to raw MongoDB JD text if ChromaDB is empty.
        print(f"[Startup] WARNING: ChromaDB rebuild failed: {e}")

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
app.include_router(chatbot_router)  # RAG chatbot — candidate + HR routes (added in v2.1.0)


@app.get("/", tags=["Health"])
async def root() -> dict:
    return {"message": "HR Recruitment Portal API is running"}


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {
        "status": "ok",
        "version": "2.1.0",
        "modules": [
            "auth", "candidate", "hr", "jobs", "applications",
            "admin", "ai", "interviewer", "interview",
            "interview_response", "retell",
            "chatbot",       # RAG chatbot + HR controls (v2.1.0)
            "skill_matcher", # SBERT-ready job matching (v2.1.0)
            "vector_store",  # ChromaDB in-memory + MongoDB embeddings (v2.1.0)
        ],
    }
