from datetime import datetime, timezone
from io import BytesIO

from bson import ObjectId
from fastapi import HTTPException, UploadFile, status

from config import settings
from database import get_database
from uploads.schemas import ProfileImageResponse

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

PROFILE_COLLECTIONS = {
    "candidate": "candidate_profiles",
    "hr": "hr_profiles",
}


def _looks_like_image(content: bytes, content_type: str) -> bool:
    signatures = {
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
        "image/webp": (b"RIFF",),
    }
    expected = signatures.get(content_type, ())
    if content_type == "image/webp":
        return content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return any(content.startswith(signature) for signature in expected)


def _configure_cloudinary() -> None:
    if not all([
        settings.CLOUDINARY_CLOUD_NAME,
        settings.CLOUDINARY_API_KEY,
        settings.CLOUDINARY_API_SECRET,
    ]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary is not configured.",
        )

    import cloudinary

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def _optimized_url(public_id: str) -> str:
    import cloudinary.utils

    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        secure=True,
        width=256,
        height=256,
        crop="fill",
        gravity="face",
        fetch_format="auto",
        quality="auto",
    )
    return url


async def upload_profile_image(user_id: str, role: str, file: UploadFile) -> ProfileImageResponse:
    if role not in PROFILE_COLLECTIONS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unsupported role for profile image upload")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WEBP images are allowed.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image file is empty.")

    if len(content) > settings.PROFILE_IMAGE_MAX_BYTES:
        max_mb = settings.PROFILE_IMAGE_MAX_BYTES / 1_000_000
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Image must be under {max_mb:g} MB.")

    if not _looks_like_image(content, file.content_type):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is not a valid image.")

    _configure_cloudinary()

    import cloudinary.uploader

    public_id = f"hirebase/{role}/profile-pictures/{user_id}/avatar"
    result = cloudinary.uploader.upload(
        BytesIO(content),
        public_id=public_id,
        overwrite=True,
        resource_type="image",
        invalidate=True,
    )

    optimized_url = _optimized_url(result["public_id"])
    now = datetime.now(timezone.utc)
    image_doc = {
        "url": optimized_url,
        "secure_url": result.get("secure_url") or optimized_url,
        "public_id": result["public_id"],
        "width": result.get("width"),
        "height": result.get("height"),
        "format": result.get("format"),
        "bytes": result.get("bytes"),
        "updated_at": now,
    }

    db = get_database()
    update_doc = {
        "avatar_url": optimized_url,
        "avatar_public_id": result["public_id"],
        "profile_image": image_doc,
    }
    await db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": update_doc})
    await db[PROFILE_COLLECTIONS[role]].update_one({"user_id": user_id}, {"$set": update_doc})

    return ProfileImageResponse(**image_doc)
