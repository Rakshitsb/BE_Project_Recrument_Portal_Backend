from fastapi import APIRouter, Depends
from app.dependencies import require_role

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users")
def get_all_users(user=Depends(require_role("ADMIN"))):
    return {"message": "Admin can view all users"}
