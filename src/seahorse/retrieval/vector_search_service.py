from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import MemorySearchResultItem
from seahorse.retrieval.conversation_recall import (
    build_conversation_search_results,
    dedupe_conversation_parent_hits,
    render_conversation_parent_hit,
)


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

        parent_hits = []
        for payload in payloads:
            parent_hit = render_conversation_parent_hit(payload)
            if parent_hit is None:
                continue
            parent_hits.append(parent_hit)

        deduped_parent_hits = dedupe_conversation_parent_hits(parent_hits)
        results: list[MemorySearchResultItem] = build_conversation_search_results(
            deduped_parent_hits
        )

        logger.debug(
            "vector_search.completed",
            {
                "result_count": len(results),
                "child_hit_count": len(parent_hits),
                "parent_result_count": len(deduped_parent_hits),
            },
        )
        return results
