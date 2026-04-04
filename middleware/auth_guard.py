from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.utils import decode_access_token
from database import get_database

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials

    payload = decode_access_token(token)
    user_id: str = payload.get("sub")
    role: str = payload.get("role")

    db = get_database()
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"id": str(user["_id"]), "email": user["email"], "role": role}


def _require_role(role: str):
    async def guard(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden",
            )
        return current_user
    return guard


require_candidate = _require_role("candidate")
require_hr        = _require_role("hr")
require_admin     = _require_role("admin")
