from fastapi import HTTPException, status
from retell import Retell

from config import settings
from database import get_database
from interview.service import create_response
from supabase_client import get_supabase


retell_client = Retell(api_key=settings.RETELL_API_KEY)


async def register_call(
    interview_id: str,
    candidate_id: str,
    interviewer_id: str,
) -> dict:
    supabase = get_supabase()

    interview_result = (
        supabase.table("interview")
        .select("*")
        .eq("id", interview_id)
        .single()
        .execute()
    )
    interview = interview_result.data

    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    if interview["candidate_id"] != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this interview",
        )

    if interview["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This interview has already been completed",
        )

    if interview["status"] == "expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This interview link has expired",
        )

    interviewer_result = (
        supabase.table("interviewer")
        .select("*")
        .eq("id", interviewer_id)
        .single()
        .execute()
    )
    interviewer = interviewer_result.data

    if interviewer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interviewer not found",
        )

    db = get_database()
    profile = await db["candidates"].find_one({"user_id": candidate_id})
    candidate_name = profile["full_name"] if profile else "Candidate"

    questions = interview["questions"]
    formatted_questions = "\n".join(
        f"{index + 1}. {question['question']}"
        for index, question in enumerate(questions)
    )

    try:
        call = retell_client.call.create_web_call(
            agent_id=interviewer["agent_id"],
            retell_llm_dynamic_variables={
                "mins": str(interview["duration_mins"]),
                "name": str(candidate_name),
                "objective": str(interview["objective"]),
                "questions": str(formatted_questions),
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register call with Retell: {str(exc)}",
        ) from exc

    await create_response(
        interview_id=interview_id,
        candidate_id=candidate_id,
        call_id=call.call_id,
    )

    return {
        "access_token": call.access_token,
        "call_id": call.call_id,
        "interview_name": interview["name"],
        "candidate_name": candidate_name,
        "duration_mins": interview["duration_mins"],
    }
