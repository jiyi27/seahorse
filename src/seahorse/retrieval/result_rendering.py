from __future__ import annotations

from seahorse.domain.models import MemorySearchResultItem
from seahorse.retrieval.conversation_recall import (
    build_conversation_search_results,
    render_conversation_parent_hit,
)


def render_vector_search_result(payload: dict[str, object]) -> MemorySearchResultItem | None:
    parent_hit = render_conversation_parent_hit(payload)
    if parent_hit is None:
        return None

    return build_conversation_search_results([parent_hit])[0]
