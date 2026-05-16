from pydantic import BaseModel


class ProfileImageResponse(BaseModel):
    url: str
    secure_url: str
    public_id: str
    width: int | None = None
    height: int | None = None
    format: str | None = None
    bytes: int | None = None

