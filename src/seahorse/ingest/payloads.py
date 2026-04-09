from __future__ import annotations

from typing import Any

from seahorse.ingest.models import ConversationChunk


def build_chunk_payload(chunk: ConversationChunk) -> dict[str, Any]:
    roles_present = sorted({message.role for message in chunk.messages})
    user_text = "\n\n".join(
        message.text.strip()
        for message in chunk.messages
        if message.role == "user" and message.text.strip()
    )
    assistant_text = "\n\n".join(
        message.text.strip()
        for message in chunk.messages
        if message.role == "assistant" and message.text.strip()
    )

    return {
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.chunk_index,
        "chunk_version": chunk.chunk_version,
        "session_id": chunk.session_id,
        "start_message_index": chunk.start_message_index,
        "end_message_index": chunk.end_message_index,
        "roles_present": roles_present,
        "user_text": user_text,
        "assistant_text": assistant_text,
        "has_tool_messages": any(message.role == "tool" for message in chunk.messages),
        "messages": [message.model_dump() for message in chunk.messages],
    }
