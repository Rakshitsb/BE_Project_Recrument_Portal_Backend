import io
from bson import ObjectId
import docx
import pdfplumber
from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from ai.schemas import JDParseResponse, MatchJobRequest, MatchJobResponse
from ai.service import MODEL, get_match_result, parse_jd_with_groq
from ai_services.cover_letter_generator import generate_cover_letter
from ai_services.resume_parser import parse_resume
from database import get_database
from middleware.auth_guard import require_candidate, require_hr

class CoverLetterRequest(BaseModel):
    job_id: str

router = APIRouter(prefix="/ai", tags=["AI Services"])
_ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB

def _extract_text(file_bytes: bytes, content_type: str) -> str:
    stream = io.BytesIO(file_bytes)
    if content_type == "application/pdf":
        text = ""
        with pdfplumber.open(stream) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text.strip()
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "\n".join(para.text for para in docx.Document(stream).paragraphs).strip()
    if content_type == "text/plain":
        return file_bytes.decode("utf-8", errors="ignore").strip()
    return ""

@router.post("/parse-resume")
async def parse_resume_route(file: UploadFile = File(...), current_user: dict = Depends(require_candidate)) -> dict:
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF, DOCX, and TXT files are allowed.")
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size must be under 5 MB.")
    text = _extract_text(file_bytes, file.content_type)
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not extract text from the file. It may be empty or image-based.")
    return await parse_resume(text)

@router.post("/generate-cover-letter")
async def generate_cover_letter_route(request: CoverLetterRequest, current_user: dict = Depends(require_candidate)) -> dict:
    candidate_id = current_user["id"]
    db = get_database()
    candidate = await db["candidate_profiles"].find_one({"user_id": candidate_id})
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found. Please complete your profile first.")
    job = await db["jobs"].find_one({"_id": ObjectId(request.job_id)})
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    hr_profile = await db["hr_profiles"].find_one({"user_id": job["hr_id"]})
    company_name = hr_profile.get("company_name", "the company") if hr_profile else "the company"
    candidate_profile = {k: candidate.get(k, "" if k != "skills" else []) for k in ["full_name", "skills", "experience_years", "education", "bio"]}
    job_data = {"title": job.get("title", ""), "description": job.get("description", ""), "required_skills": job.get("required_skills", []), "company_name": company_name, "hr_id": job.get("hr_id")}
    return await generate_cover_letter(candidate_profile, job_data)


@router.post("/parse-jd", response_model=JDParseResponse)
async def parse_jd_route(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_hr),
) -> JDParseResponse:
    """Parse an uploaded JD file into dynamic structured JSON using Groq AI."""
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF, DOCX, and TXT files are allowed.")
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size must be under 5 MB.")
    text = _extract_text(file_bytes, file.content_type)
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not extract text from the file. It may be empty or image-based.")
    parsed_jd = await parse_jd_with_groq(text)
    return JDParseResponse(
        parsed_jd=parsed_jd,
        raw_text=text,
        model_used=MODEL,
    )


@router.post(
    "/match-job",
    response_model=MatchJobResponse,
    status_code=status.HTTP_200_OK,
)
async def match_job_route(
    request: MatchJobRequest,
    current_user: dict = Depends(require_candidate),
) -> MatchJobResponse:
    """Score a candidate's profile against a job using embedding-based matching."""
    db = get_database()
    candidate_id = current_user["id"]
    return await get_match_result(db, candidate_id, request.job_id)
