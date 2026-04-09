from __future__ import annotations

from seahorse.ingest.models import ConversationChunk


EMBEDDING_ROLES = {"user", "assistant"}


def build_embedding_text(chunk: ConversationChunk) -> str:
    parts: list[str] = []
    for message in chunk.messages:
        if message.role not in EMBEDDING_ROLES:
            continue
        text = message.text.strip()
        if not text:
            continue
        parts.append(f"[{message.role}]\n{text}")
    return "\n\n".join(parts)
