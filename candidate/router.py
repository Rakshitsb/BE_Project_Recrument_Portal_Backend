from fastapi import APIRouter, Depends, File, UploadFile

from candidate.schemas import CandidateProfileCreate, CandidateProfileUpdate, CandidateProfileResponse
from candidate.service import create_profile, get_profile, update_profile, delete_profile
from middleware.auth_guard import require_candidate
from uploads.schemas import ProfileImageResponse
from uploads.service import upload_profile_image

router = APIRouter(prefix="/candidate", tags=["Candidate"])


@router.post("/avatar", response_model=ProfileImageResponse)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: dict = Depends(require_candidate),
) -> ProfileImageResponse:
    return await upload_profile_image(current_user["id"], "candidate", avatar)


@router.post("/profile", response_model=CandidateProfileResponse, status_code=201)
async def create(
    data: CandidateProfileCreate,
    current_user: dict = Depends(require_candidate),
) -> CandidateProfileResponse:
    return await create_profile(current_user["id"], data)


@router.get("/profile", response_model=CandidateProfileResponse)
async def get(
    current_user: dict = Depends(require_candidate),
) -> CandidateProfileResponse:
    return await get_profile(current_user["id"])


@router.put("/profile", response_model=CandidateProfileResponse)
async def update(
    data: CandidateProfileUpdate,
    current_user: dict = Depends(require_candidate),
) -> CandidateProfileResponse:
    return await update_profile(current_user["id"], data)


@router.delete("/profile", status_code=200)
async def delete(
    current_user: dict = Depends(require_candidate),
) -> dict:
    return await delete_profile(current_user["id"])
