from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import MemorySearchResultItem
from seahorse.retrieval.result_rendering import render_vector_search_result


class VectorSearchService:
    def __init__(self, embedding_model, vector_store, *, top_k: int) -> None:
        self._embedding_model = embedding_model
        self._vector_store = vector_store
        self._top_k = top_k

    def search(self, query: str) -> list[MemorySearchResultItem]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        logger.debug(
            "vector_search.started",
            {"query_len": len(normalized_query), "top_k": self._top_k},
        )
        query_vector = self._embedding_model.embed_documents([normalized_query])[0]
        payloads = self._vector_store.search_chunks(
            query_vector=query_vector,
            limit=self._top_k,
        )

        results: list[MemorySearchResultItem] = []
        for payload in payloads:
            rendered = render_vector_search_result(payload)
            if rendered is not None:
                results.append(rendered)

        logger.debug("vector_search.completed", {"result_count": len(results)})
        return results
