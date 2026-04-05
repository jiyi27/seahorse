from __future__ import annotations

from seahorse.application.ingest_service import IngestService
from seahorse.domain.models import ConversationInput, Message


def ingest_turn(
    service: IngestService,
    *,
    content: str | None = None,
    messages: list[dict[str, str]] | None = None,
    source: str = "mcp",
    session_id: str | None = None,
) -> dict[str, object]:
    normalized_messages = [
        Message(role=message["role"], text=message["text"])
        for message in (messages or [])
    ]
    conversation = ConversationInput(
        source=source,
        content=content,
        messages=normalized_messages,
        session_id=session_id,
    )
    result = service.ingest(conversation)
    return {
        "user_model_updated": result.user_model_updated,
        "user_model": result.user_model.content,
        "version": result.user_model.version,
    }
