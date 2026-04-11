from __future__ import annotations

from seahorse.ingest.models import ConversationBlock


EXCLUDED_CONTENT_ROLES = {"system"}


def build_block_content(block: ConversationBlock) -> str:
    parts: list[str] = []
    for message in block.messages:
        if message.role in EXCLUDED_CONTENT_ROLES:
            continue
        text = message.text.strip()
        if not text:
            continue
        parts.append(f"[{message.role}]\n{text}")
    return "\n\n".join(parts)
