import json

from fastapi import APIRouter, HTTPException, Request

from retell.logging import logger
from retell.schemas import RetellWebhookEvent, WebhookAckResponse
from retell.service import (
    handle_call_ended,
    handle_call_started,
    verify_retell_signature,
)
from retell.service_analyzed import handle_call_analyzed

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/retell", response_model=WebhookAckResponse)
async def retell_webhook(request: Request) -> WebhookAckResponse:
    raw_body = await request.body()
    signature = request.headers.get("x-retell-signature", "")
    if not signature:
        raise HTTPException(401, "Missing x-retell-signature header")
    if not verify_retell_signature(raw_body, signature):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        event_data = RetellWebhookEvent(**json.loads(raw_body))
        match event_data.event:
            case "call_started":
                await handle_call_started(event_data.call)
            case "call_ended":
                await handle_call_ended(event_data.call)
            case "call_analyzed":
                await handle_call_analyzed(event_data.call)
            case _:
                pass
        return WebhookAckResponse(received=True, event=event_data.event)
    except Exception as e:
        logger.error("Retell webhook handling failed: %s", e)
        return WebhookAckResponse(received=True, event="unknown")
