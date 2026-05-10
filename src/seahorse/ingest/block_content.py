from __future__ import annotations

from seahorse.ingest.models import ConversationBlock


def build_block_content(block: ConversationBlock) -> str:
    parts: list[str] = []
    for message in block.messages:
        text = message.text.strip()
        if not text:
            continue
        parts.append(f"[{message.role}]\n{text}")
    return "\n\n".join(parts)
