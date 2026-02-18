from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends
from app.services.ai.resume_extractor import ResumeExtractor
from app.services.ai.llm_service import LLMService
from app.services.ai.embedding_service import EmbeddingService
from app.schemas.candidate_schema import (
    ResumeData,
    CreateProfileRequest,
    CandidateProfile,
)
from app.db.database import candidate_collection
from datetime import datetime
from typing import List

router = APIRouter(prefix="/candidate", tags=["Candidate"])

# Dependency Injection for Services
# In a real app, you might use a more sophisticated DI container
llm_service = LLMService()
embedding_service = EmbeddingService()


def get_llm_service():
    return llm_service


def get_embedding_service():
    return embedding_service


@router.post("/extract-resume", response_model=ResumeData)
async def extract_resume(
    file: UploadFile = File(...), llm: LLMService = Depends(get_llm_service)
):
    """
    Upload a resume (PDF/DOCX), extract text, and parse it using LLM into structured JSON.
    """
    # 1. Extract Text
    text = await ResumeExtractor.extract_text(file)

    # 2. Extract Data using LLM
    try:
        extracted_data = llm.extract_resume_data(text)
        return extracted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-profile", response_model=CandidateProfile)
async def create_profile(
    profile_data: CreateProfileRequest,
    embedder: EmbeddingService = Depends(get_embedding_service),
):
    """
    Accepts final edited profile data, generates embeddings, and stores in MongoDB.
    """
    # 1. Generate Summary for Embedding
    # Combine key fields to create a rich semantic representation
    summary_parts = [
        f"Name: {profile_data.full_name}",
        f"Skills: {', '.join(profile_data.skills)}",
        "Experience: "
        + "; ".join(
            [f"{exp.role} at {exp.company}" for exp in profile_data.experience]
        ),
        "Education: "
        + "; ".join(
            [f"{edu.degree} at {edu.institution}" for edu in profile_data.education]
        ),
        f"Projects: {', '.join([p.name for p in profile_data.projects])}",
    ]
    summary_text = ". ".join(summary_parts)

    # 2. Generate Embedding
    embedding = embedder.generate_embedding(summary_text)

    # 3. Prepare DB Document
    new_profile = profile_data.model_dump(by_alias=True)
    new_profile["resume_embedding"] = embedding
    new_profile["created_at"] = datetime.utcnow()
    new_profile["updated_at"] = datetime.utcnow()

    # 4. Insert into MongoDB
    result = candidate_collection.insert_one(new_profile)

    # 5. Return Created Profile
    created_profile = candidate_collection.find_one({"_id": result.inserted_id})

    # Handle ObjectId to string conversion naturally via Pydantic model alias="_id"
    # But PyMongo returns ObjectId, so we might need to cast it or let Pydantic handle it if configured.
    # The schema has `id: str = Field(..., alias="_id")`, so we need to ensure the `_id` in dict is converted to str
    # OR simpler: just return what we have and let custom encoders handle it.

    encoded_profile = created_profile
    encoded_profile["_id"] = str(encoded_profile["_id"])  # helper for pydantic

    return encoded_profile
