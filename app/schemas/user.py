from pydantic import BaseModel, EmailStr,validator

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # USER or HR

    @validator("role")
    def validate_role(cls, value):
        allowed_roles = ["USER", "HR"]
        if value not in allowed_roles:
            raise ValueError("Role must be USER or HR")
        return value