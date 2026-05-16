"""Pydantic schemas for the candidate-facing chatbot API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    id: str
    role: str  # "user" | "assistant" | "hr"
    content: str
    timestamp: datetime
    modal_payload: Optional[dict] = None
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ChatSessionSummary(BaseModel):
    """Lightweight session list item — no messages array."""

    id: str
    job_id: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_logo_url: Optional[str] = None
    is_enabled: bool
    enabled_at: Optional[datetime] = None
    message_count: int
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChatSessionDetail(BaseModel):
    """Full session detail including all messages."""

    id: str
    job_id: str
    is_enabled: bool
    messages: list[MessageOut] = []
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SendMessageResponse(BaseModel):
    """Both the saved user message and the AI reply returned together."""

    user_message: MessageOut
    assistant_message: MessageOut


# ---------------------------------------------------------------------------
# HR schemas (added in Prompt 6)
# ---------------------------------------------------------------------------


class ChatbotStatusResponse(BaseModel):
    """Status of a chatbot session — returned after enable/disable actions."""

    job_id: str
    candidate_id: str
    is_enabled: bool
    enabled_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None
    message_count: int
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class HRSessionListItem(BaseModel):
    """Lightweight session list item for HR's job-wide session view."""

    id: str
    job_id: str
    candidate_id: str
    is_enabled: bool
    message_count: int
    updated_at: Optional[datetime] = None
    candidate_name: Optional[str] = None
    candidate_avatar_url: Optional[str] = None
    job_title: Optional[str] = None

    model_config = {"from_attributes": True}


class HRSessionDetail(BaseModel):
    """Full session detail including all messages — HR view."""

    id: str
    job_id: str
    candidate_id: str
    candidate_name: Optional[str] = None
    candidate_avatar_url: Optional[str] = None
    is_enabled: bool
    messages: list[MessageOut] = []
    enabled_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# HR personalized message schemas (added in Prompt 7)
# ---------------------------------------------------------------------------


class HRSendMessageRequest(BaseModel):
    """Request body for HR sending a personalized message into a candidate's chat."""

    message: str = Field(..., min_length=1, max_length=2000)
    interview_link: Optional[str] = None
    interview_id: Optional[str] = None
    message_type: str = "general"  # "general" | "interview_invite"


class HRSendMessageResponse(BaseModel):
    """Response after HR sends a personalized message."""

    hr_message: MessageOut
    session_id: str
    candidate_id: str
    job_id: str
