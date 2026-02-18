from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.db.database import user_collection
from app.core.security import create_access_token
from app.schemas.user import UserCreate

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = user_collection.find_one({"email": form_data.username})

    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        {"sub": user["email"], "id": str(user["_id"]), "role": user["role"]}
    )

    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@router.post("/signup")
def signup(user: UserCreate):
    # Check duplicate email
    if user_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = {
        "name": user.name,
        "email": user.email,
        "password": user.password,  # plain text
        "role": user.role,  # USER or HR only
    }

    user_collection.insert_one(new_user)

    return {"message": "Signup successful", "email": user.email, "role": user.role}
