import asyncio
import json

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from retell import Retell

from ai_services.communication_analysis import analyze_communication
from ai_services.interview_analytics import generate_analytics
from config import settings
from interview.service import save_response_analytics
from supabase_client import get_supabase


retell_client = Retell(api_key=settings.RETELL_API_KEY)


def _merge_analytics(
    analytics: dict,
    communication: dict,
) -> dict:
    return {
        "overall_score": analytics["overallScore"],
        "overall_feedback": analytics["overallFeedback"],
        "communication": {
            "score": communication["communicationScore"],
            "feedback": communication["overallFeedback"],
        },
        "question_summaries": analytics["questionSummaries"],
        "soft_skill_summary": analytics["softSkillSummary"],
        "main_interview_questions": analytics.get(
            "mainInterviewQuestions", []
        ),
        "supporting_quotes": communication["supportingQuotes"],
        "strengths": communication["strengths"],
        "improvement_areas": communication["improvementAreas"],
    }


async def handle_retell_webhook(
    body: dict,
    signature: str = "",
) -> dict:
    verify_signature = getattr(settings, "RETELL_VERIFY_SIGNATURE", True)

    if verify_signature:
        try:
            is_valid = Retell.verify(
                json.dumps(body),
                settings.RETELL_API_KEY,
                signature,
            )
            if not is_valid:
                return {"status": "unauthorized"}
        except Exception:
            return {"status": "unauthorized"}

    event = body.get("event", "")
    call = body.get("call", {})
    call_id = call.get("call_id", "")

    if event == "call_started":
        return {"status": "ok", "event": "call_started"}

    if event == "call_ended":
        return {"status": "ok", "event": "call_ended"}

    if event == "call_analyzed":
        return await _handle_call_analyzed(call)

    return {"status": "ok", "event": "unknown"}


async def _handle_call_analyzed(call: dict) -> dict:
    call_id = call.get("call_id", "")
    transcript = call.get("transcript", "")
    start_timestamp = call.get("start_timestamp", 0)
    end_timestamp = call.get("end_timestamp", 0)

    duration = 0
    if start_timestamp and end_timestamp:
        duration = round((end_timestamp - start_timestamp) / 1000)

    supabase = get_supabase()
    response_result = (
        supabase.table("response")
        .select("*")
        .eq("call_id", call_id)
        .single()
        .execute()
    )
    response_doc = response_result.data

    if response_doc is None:
        return {"status": "error", "detail": "Response not found"}

    interview_id = response_doc["interview_id"]
    interview_result = (
        supabase.table("interview")
        .select("*")
        .eq("id", interview_id)
        .single()
        .execute()
    )
    interview = interview_result.data

    if interview is None:
        return {"status": "error", "detail": "Interview not found"}

    questions = [
        question["question"] for question in interview.get("questions", [])
    ]

    if not transcript or not transcript.strip():
        return {
            "status": "error",
            "detail": "Empty transcript received",
        }

    try:
        analytics_result, communication_result = await asyncio.gather(
            generate_analytics(transcript, questions),
            analyze_communication(transcript),
        )
    except Exception as exc:
        return {
            "status": "error",
            "detail": f"AI analysis failed: {str(exc)}",
        }

    merged = _merge_analytics(analytics_result, communication_result)

    try:
        await save_response_analytics(
            call_id=call_id,
            details=call,
            analytics=merged,
            duration=duration,
        )
    except Exception as exc:
        return {
            "status": "error",
            "detail": f"Failed to save analytics: {str(exc)}",
        }

    return {
        "status": "ok",
        "event": "call_analyzed",
        "call_id": call_id,
    }
