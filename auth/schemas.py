from typing import Literal
from pydantic import BaseModel, EmailStr, Field


# --- Role type alias ---
Role = Literal["candidate", "hr", "admin"]


# --- Request schemas ---
class UserSignup(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    role: Role  # no default — must be explicitly provided


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=72)


# --- Response schemas ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class UserInDB(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role

    model_config = {"from_attributes": True}
