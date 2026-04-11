from __future__ import annotations

from seahorse.domain.models import MemorySearchResultItem
from seahorse.ingest.vector_fields import CONTENT, PARENT_BLOCK_ID


def render_vector_search_result(payload: dict[str, object]) -> MemorySearchResultItem | None:
    parent_block_id = payload.get(PARENT_BLOCK_ID)
    if not isinstance(parent_block_id, str) or not parent_block_id:
        return None

    text = _normalize_text(payload.get(CONTENT))
    if not text:
        return None

    return MemorySearchResultItem(
        id=parent_block_id,
        source_type="conversation",
        text=text,
    )


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
