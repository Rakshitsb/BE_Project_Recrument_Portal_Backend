from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

# --- Password hashing ---
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_BCRYPT_MAX_BYTES = 72


def _password_too_long(password: str) -> bool:
    return len(password.encode("utf-8")) > _BCRYPT_MAX_BYTES


def hash_password(password: str) -> str:
    if _password_too_long(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be 72 bytes or fewer.",
        )
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if _password_too_long(plain):
        return False

    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


# --- JWT ---
def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(data["user_id"]),
        "role": data["role"],
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
