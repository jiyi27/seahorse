from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import MemorySearchResultItem


class MemorySearchService:
    def __init__(
        self,
        *,
        vector_search_service=None,
    ) -> None:
        self._vector_search_service = vector_search_service

    def search(self, query: str) -> list[MemorySearchResultItem]:
        normalized_query = query.strip()

        logger.debug(
            "memory_search.started",
            {"query_len": len(normalized_query)},
        )

        if not normalized_query:
            logger.debug("memory_search.completed", {"result_count": 0})
            return []

        if self._vector_search_service is None:
            logger.debug("memory_search.completed", {"result_count": 0})
            return []

        results = self._vector_search_service.search(normalized_query)
        logger.debug(
            "memory_search.completed",
            {"result_count": len(results), "source": "vector"},
        )
        return results
