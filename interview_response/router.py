from fastapi import APIRouter, Depends

from interview_response.schemas import CandidateResponseOut, InterviewResponseOut, InterviewResponseSummary, ResponseStatusUpdate, TabSwitchUpdate
from interview_response.service import get_my_response, record_tab_switch
from interview_response.service_hr import get_response_detail, get_responses_by_interview, update_response_status
from middleware.auth_guard import require_candidate, require_hr

router = APIRouter(prefix="/interview-responses", tags=["Interview Responses"])


@router.get("/my/{interview_id}", response_model=CandidateResponseOut)
async def my_response(interview_id: str, current_user: dict = Depends(require_candidate)) -> CandidateResponseOut:
    return await get_my_response(interview_id, current_user["id"])


@router.patch("/my/tab-switch/{call_id}", response_model=dict, status_code=200)
async def patch_tab_switch(call_id: str, data: TabSwitchUpdate, current_user: dict = Depends(require_candidate)) -> dict:
    return await record_tab_switch(call_id, current_user["id"], data)


@router.get("/{interview_id}", response_model=list[InterviewResponseSummary])
async def list_responses(interview_id: str, current_user: dict = Depends(require_hr)) -> list[InterviewResponseSummary]:
    return await get_responses_by_interview(interview_id, current_user["id"])


@router.get("/{interview_id}/{response_id}", response_model=InterviewResponseOut)
async def response_detail(interview_id: str, response_id: str, current_user: dict = Depends(require_hr)) -> InterviewResponseOut:
    return await get_response_detail(response_id, current_user["id"])


@router.patch("/{response_id}/status", response_model=InterviewResponseOut)
async def patch_status(response_id: str, data: ResponseStatusUpdate, current_user: dict = Depends(require_hr)) -> InterviewResponseOut:
    return await update_response_status(response_id, current_user["id"], data)
