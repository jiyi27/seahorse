from __future__ import annotations

from seahorse.application.session_ingest_service import SessionIngestService
from seahorse.domain.models import (
    ConversationInput,
    Message,
)
from seahorse.tools.contracts import (
    IngestTurnSuccess,
    IngestTurnResult,
    ToolInputMessage,
    internal_error,
)
from seahorse.tools.tool_hints import INGEST_RETRY_HINT


def ingest_turn(
    service: SessionIngestService,
    *,
    content: str | None = None,
    messages: list[Message | ToolInputMessage] | None = None,
    session_id: str | None = None,
) -> IngestTurnResult:
    normalized_messages = [
        message
        if isinstance(message, Message)
        else Message(role=message["role"], text=message["text"])
        for message in (messages or [])
    ]
    conversation = ConversationInput(
        content=content,
        messages=normalized_messages,
        session_id=session_id,
    )
    try:
        result = service.ingest(conversation)
    except RuntimeError as exc:
        return internal_error(str(exc), INGEST_RETRY_HINT)

    payload: IngestTurnSuccess = {
        "success": True,
        "user_profile_updated": result.user_profile_updated,
    }
    return payload
