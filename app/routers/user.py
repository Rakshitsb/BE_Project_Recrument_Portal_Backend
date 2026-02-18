from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/profile")
def profile(user=Depends(get_current_user)):
    return {"id": user["id"], "role": user["role"]}
