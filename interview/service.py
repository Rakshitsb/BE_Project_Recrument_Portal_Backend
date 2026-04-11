from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from nanoid import generate

from supabase_client import get_supabase
from database import get_database
from config import settings
from interview.schemas import (
    InterviewCreate,
    InterviewUpdate,
    InterviewResponse,
    InterviewStatus,
    ResponseRecord,
    AnalyticsResponse,
)


# ── Helper Functions ──────────────────────────────────────────────────────────


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")


def _to_interview_response(doc: dict) -> InterviewResponse:
    return InterviewResponse(
        id=doc["id"],
        application_id=doc["application_id"],
        job_id=doc["job_id"],
        hr_id=doc["hr_id"],
        candidate_id=doc["candidate_id"],
        name=doc["name"],
        objective=doc["objective"],
        questions=doc["questions"],
        interviewer_id=doc["interviewer_id"],
        duration_mins=doc["duration_mins"],
        status=InterviewStatus(doc["status"]),
        interview_url=doc["interview_url"],
        readable_slug=doc["readable_slug"],
        insights=doc.get("insights") or [],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _to_response_record(doc: dict) -> ResponseRecord:
    analytics = None
    if doc.get("analytics") is not None:
        analytics = AnalyticsResponse(**doc["analytics"])

    return ResponseRecord(
        id=doc["id"],
        interview_id=doc["interview_id"],
        candidate_id=doc["candidate_id"],
        call_id=doc["call_id"],
        is_ended=doc.get("is_ended", False),
        is_analysed=doc.get("is_analysed", False),
        duration=doc.get("duration"),
        details=doc.get("details"),
        analytics=analytics,
        created_at=doc["created_at"],
    )


# ── Interview CRUD Functions ─────────────────────────────────────────────────


async def create_interview(hr_id: str, data: InterviewCreate) -> InterviewResponse:
    db = get_database()
    supabase = get_supabase()

    # Verify application exists (MongoDB)
    app = await db["applications"].find_one({"_id": _oid(data.application_id)})
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if app["status"] != "shortlisted":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Candidate must be shortlisted before creating an interview",
        )

    # Verify job exists (MongoDB)
    job = await db["jobs"].find_one({"_id": _oid(data.job_id)})
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    candidate_id = app["candidate_id"]

    # Check no duplicate interview (Supabase)
    result = supabase.table("interview").select("id").eq("application_id", data.application_id).execute()
    if result.data:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Interview already exists for this application",
        )

    # Generate slug and URL
    unique_id = generate(size=8)
    name_slug = data.name.lower().replace(" ", "-")
    readable_slug = f"{name_slug}-{unique_id}"
    interview_url = f"{settings.BASE_URL}/interviews/{readable_slug}"

    # Insert into Supabase
    result = supabase.table("interview").insert({
        "application_id": data.application_id,
        "job_id": data.job_id,
        "hr_id": hr_id,
        "candidate_id": candidate_id,
        "name": data.name,
        "objective": data.objective,
        "questions": [q.model_dump() for q in data.questions],
        "interviewer_id": data.interviewer_id,
        "duration_mins": data.duration_mins,
        "status": InterviewStatus.pending,
        "interview_url": interview_url,
        "readable_slug": readable_slug,
        "insights": [],
    }).execute()

    return _to_interview_response(result.data[0])


async def get_interviews_by_hr(hr_id: str) -> list[InterviewResponse]:
    supabase = get_supabase()
    result = supabase.table("interview").select("*").eq("hr_id", hr_id).order("created_at", desc=True).execute()
    return [_to_interview_response(doc) for doc in result.data]


async def get_interview_by_id(
    interview_id: str, requester_id: str, requester_role: str
) -> InterviewResponse:
    supabase = get_supabase()
    result = supabase.table("interview").select("*").eq("id", interview_id).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")

    if requester_role == "hr" and doc["hr_id"] != requester_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    if requester_role == "candidate" and doc["candidate_id"] != requester_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    return _to_interview_response(doc)


async def get_interview_by_slug(slug: str) -> InterviewResponse:
    supabase = get_supabase()
    result = supabase.table("interview").select("*").eq("readable_slug", slug).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")

    return _to_interview_response(doc)


async def update_interview(
    interview_id: str, hr_id: str, data: InterviewUpdate
) -> InterviewResponse:
    supabase = get_supabase()
    result = supabase.table("interview").select("*").eq("id", interview_id).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    if doc["status"] != InterviewStatus.pending:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot edit an interview that has already been taken",
        )

    updates = data.model_dump(exclude_none=True)
    if "questions" in updates:
        updates["questions"] = [q.model_dump() for q in data.questions]

    result = supabase.table("interview").update(updates).eq("id", interview_id).execute()
    return _to_interview_response(result.data[0])


async def delete_interview(interview_id: str, hr_id: str) -> dict:
    supabase = get_supabase()
    result = supabase.table("interview").select("*").eq("id", interview_id).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    if doc["status"] != InterviewStatus.pending:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete an interview that has already been taken",
        )

    supabase.table("interview").delete().eq("id", interview_id).execute()
    return {"message": "Interview deleted successfully"}


# ── Response / Call Functions ─────────────────────────────────────────────────


async def create_response(
    interview_id: str, candidate_id: str, call_id: str
) -> ResponseRecord:
    supabase = get_supabase()
    result = supabase.table("interview").select("*").eq("id", interview_id).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if doc["candidate_id"] != candidate_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    # Update interview status to active
    supabase.table("interview").update({"status": InterviewStatus.active}).eq("id", interview_id).execute()

    # Insert response record
    result = supabase.table("response").insert({
        "interview_id": interview_id,
        "candidate_id": candidate_id,
        "call_id": call_id,
        "is_ended": False,
        "is_analysed": False,
        "duration": None,
        "details": None,
        "analytics": None,
    }).execute()

    return _to_response_record(result.data[0])


async def save_response_analytics(
    call_id: str, details: dict, analytics: dict, duration: int
) -> ResponseRecord:
    supabase = get_supabase()

    # Fetch response by call_id
    result = supabase.table("response").select("*").eq("call_id", call_id).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Response not found")

    # Update response with analytics
    result = supabase.table("response").update({
        "is_ended": True,
        "is_analysed": True,
        "duration": duration,
        "details": details,
        "analytics": analytics,
    }).eq("call_id", call_id).execute()

    # Update linked interview status to completed
    supabase.table("interview").update({"status": InterviewStatus.completed}).eq("id", doc["interview_id"]).execute()

    return _to_response_record(result.data[0])


async def get_responses_by_interview(
    interview_id: str, hr_id: str
) -> list[ResponseRecord]:
    supabase = get_supabase()

    # Verify interview exists and HR owns it
    result = supabase.table("interview").select("*").eq("id", interview_id).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if doc["hr_id"] != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    result = supabase.table("response").select("*").eq("interview_id", interview_id).eq("is_ended", True).order("created_at", desc=True).execute()
    return [_to_response_record(doc) for doc in result.data]


async def get_candidate_interviews(candidate_id: str) -> list[InterviewResponse]:
    supabase = get_supabase()
    result = supabase.table("interview").select("*").eq("candidate_id", candidate_id).order("created_at", desc=True).execute()
    return [_to_interview_response(doc) for doc in result.data]


async def update_interview_insights(
    interview_id: str, insights: list[str]
) -> None:
    supabase = get_supabase()
    supabase.table("interview").update({"insights": insights}).eq("id", interview_id).execute()
