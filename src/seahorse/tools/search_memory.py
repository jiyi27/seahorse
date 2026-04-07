from __future__ import annotations

from seahorse.application.memory_search_service import MemorySearchService
from seahorse.tools.contracts import (
    SEARCH_MEMORY_FAILED_HINT,
    SEARCH_MEMORY_HAS_RESULTS_HINT,
    SEARCH_MEMORY_NO_RESULTS_HINT,
    SearchMemoryResult,
    SearchMemorySuccess,
    internal_error,
)


def search_memory(
    service: MemorySearchService,
    *,
    query: str,
    top_k: int = 3,
) -> SearchMemoryResult:
    try:
        results = service.search(query, top_k=top_k)
    except RuntimeError as exc:
        return internal_error(str(exc), SEARCH_MEMORY_FAILED_HINT)

    payload: SearchMemorySuccess = {
        "success": True,
        "results": [
            {
                "id": item.id,
                "source_type": item.source_type,
                "text": item.text,
            }
            for item in results
        ],
        "hint": (
            SEARCH_MEMORY_HAS_RESULTS_HINT
            if results
            else SEARCH_MEMORY_NO_RESULTS_HINT
        ),
    }
    return payload
