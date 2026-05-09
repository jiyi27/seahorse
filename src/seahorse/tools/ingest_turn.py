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
) -> IngestTurnResult:
    # Normalize everything into Message so the rest of the ingest path sees one shape.
    normalized_messages: list[Message] = []
    for message in (messages or []):
        if isinstance(message, Message):
            normalized_messages.append(message)
            continue
        normalized_messages.append(
            Message(role=message["role"], text=message["text"])
        )

    # Normalize the incoming `content`/`messages` arguments into
    # ConversationInput so the ingest layer accepts a single input shape
    # instead of separate raw parameters.
    # ConversationInput also enforces that exactly one of `content` or `messages` is provided.
    conversation = ConversationInput(
        content=content,
        messages=normalized_messages,
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
