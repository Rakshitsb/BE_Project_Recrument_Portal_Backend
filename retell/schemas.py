from pydantic import BaseModel, ConfigDict


class CallAnalysis(BaseModel):
    call_summary: str | None = None
    user_sentiment: str | None = None
    agent_task_completion_rating: str | None = None
    call_completion_rating: str | None = None


class RetellCallPayload(BaseModel):
    call_id: str
    call_status: str | None = None
    start_timestamp: int | None = None
    end_timestamp: int | None = None
    transcript: str | None = None
    recording_url: str | None = None
    call_analysis: CallAnalysis | None = None
    model_config = ConfigDict(extra="allow")


class RetellWebhookEvent(BaseModel):
    event: str
    call: RetellCallPayload


class WebhookAckResponse(BaseModel):
    received: bool = True
    event: str
