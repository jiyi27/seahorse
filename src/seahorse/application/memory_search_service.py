from __future__ import annotations

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

        if not normalized_query:
            return []

        if self._vector_search_service is None:
            return []

        return self._vector_search_service.search(normalized_query)
