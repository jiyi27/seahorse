from __future__ import annotations

from dataclasses import dataclass

from seahorse.domain.models import MemorySearchResultItem
from seahorse.ingest.vector_fields import CONTENT, PARENT_BLOCK_ID


@dataclass(frozen=True)
class ConversationParentHit:
    parent_block_id: str
    content: str


def render_conversation_parent_hit(
    payload: dict[str, object],
) -> ConversationParentHit | None:
    parent_block_id = _normalize_text(payload.get(PARENT_BLOCK_ID))
    if not parent_block_id:
        return None

    content = _normalize_text(payload.get(CONTENT))
    if not content:
        return None

    return ConversationParentHit(
        parent_block_id=parent_block_id,
        content=content,
    )


def dedupe_conversation_parent_hits(
    hits: list[ConversationParentHit],
) -> list[ConversationParentHit]:
    deduped_hits: list[ConversationParentHit] = []
    seen_parent_block_ids: set[str] = set()
    for hit in hits:
        if hit.parent_block_id in seen_parent_block_ids:
            continue
        seen_parent_block_ids.add(hit.parent_block_id)
        deduped_hits.append(hit)
    return deduped_hits


def build_conversation_search_results(
    hits: list[ConversationParentHit],
) -> list[MemorySearchResultItem]:
    return [
        MemorySearchResultItem(
            id=hit.parent_block_id,
            source_type="conversation",
            text=hit.content,
        )
        for hit in hits
    ]


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
