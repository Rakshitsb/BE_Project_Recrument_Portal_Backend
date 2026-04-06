import io

import docx
import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ai_services.resume_parser import parse_resume
from middleware.auth_guard import require_candidate

router = APIRouter(prefix="/ai", tags=["AI Services"])

_ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _extract_text(file_bytes: bytes, content_type: str) -> str:
    """Extract plain text from PDF, DOCX, or TXT bytes."""
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
        doc = docx.Document(stream)
        return "\n".join(para.text for para in doc.paragraphs).strip()

    if content_type == "text/plain":
        return file_bytes.decode("utf-8", errors="ignore").strip()

    return ""


@router.post("/parse-resume")
async def parse_resume_route(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_candidate),
) -> dict:

    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOCX, and TXT files are allowed.",
        )

    file_bytes = await file.read()

    if len(file_bytes) > _MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be under 5 MB.",
        )

    text = _extract_text(file_bytes, file.content_type)

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the file. It may be empty or image-based.",
        )

    return await parse_resume(text)