from fastapi import APIRouter, Depends
from app.dependencies import require_role

router = APIRouter(prefix="/hr", tags=["HR"])

@router.post("/post-job")
def post_job(user=Depends(require_role("HR"))):
    return {"message": "HR can post jobs"}

@router.get("/applications")
def view_applications(user=Depends(require_role("HR"))):
    return {"message": "HR can view applications"}
