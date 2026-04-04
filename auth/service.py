from datetime import datetime, timezone

from fastapi import HTTPException, status

from database import get_database
from auth.schemas import UserSignup, UserLogin, TokenResponse, UserInDB
from auth.utils import hash_password, verify_password, create_access_token


async def signup_user(data: UserSignup) -> UserInDB:
    db = get_database()
    users = db["users"]

    existing = await users.find_one({"email": data.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = {
        "name": data.name,
        "email": data.email,
        "hashed_password": hash_password(data.password),
        "role": data.role,
        "created_at": datetime.now(timezone.utc),
    }
    result = await users.insert_one(new_user)

    return UserInDB(
        id=str(result.inserted_id),
        name=data.name,
        email=data.email,
        role=data.role,
    )


async def login_user(data: UserLogin) -> TokenResponse:
    db = get_database()
    users = db["users"]

    user = await users.find_one({"email": data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"user_id": str(user["_id"]), "role": user["role"]})
    return TokenResponse(access_token=token, role=user["role"])
