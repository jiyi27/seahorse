from __future__ import annotations

from seahorse.domain.models import MemorySearchResultItem


def render_vector_search_result(payload: dict[str, object]) -> MemorySearchResultItem | None:
    chunk_id = payload.get("chunk_id")
    if not isinstance(chunk_id, str) or not chunk_id:
        return None

    assistant_text = _normalize_text(payload.get("assistant_text"))
    user_text = _normalize_text(payload.get("user_text"))
    text = assistant_text or user_text
    if not text:
        return None

    return MemorySearchResultItem(
        id=chunk_id,
        source_type="conversation",
        text=text,
    )


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
