from fastapi import APIRouter

from auth.schemas import UserSignup, UserLogin, TokenResponse, UserInDB
from auth.service import signup_user, login_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserInDB, status_code=201)
async def signup(data: UserSignup) -> UserInDB:
    return await signup_user(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin) -> TokenResponse:
    return await login_user(data)
