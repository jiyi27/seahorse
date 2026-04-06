from __future__ import annotations

from seahorse.application.ingest_service import IngestService
from seahorse.domain.models import (
    ConversationInput,
    ConversationSource,
    Message,
)
from seahorse.tools.contracts import (
    INGEST_RETRY_HINT,
    IngestTurnResult,
    ToolInputMessage,
    internal_error,
)


def ingest_turn(
    service: IngestService,
    *,
    content: str | None = None,
    messages: list[Message | ToolInputMessage] | None = None,
    source: ConversationSource = "mcp",
    session_id: str | None = None,
) -> IngestTurnResult:
    normalized_messages = [
        message
        if isinstance(message, Message)
        else Message(role=message["role"], text=message["text"])
        for message in (messages or [])
    ]
    conversation = ConversationInput(
        source=source,
        content=content,
        messages=normalized_messages,
        session_id=session_id,
    )
    try:
        result = service.ingest(conversation)
    except RuntimeError as exc:
        return internal_error(str(exc), INGEST_RETRY_HINT)

    return {
        "success": True,
        "user_model_updated": result.user_model_updated,
    }
