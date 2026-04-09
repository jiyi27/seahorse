from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import MemorySearchResultItem, UserModel
from seahorse.domain.repositories import UserModelRepository

DEFAULT_TOP_K = 3


class MemorySearchService:
    def __init__(
        self,
        user_model_repository: UserModelRepository,
        *,
        top_k: int = DEFAULT_TOP_K,
        vector_search_service=None,
    ) -> None:
        self._user_model_repository = user_model_repository
        self._top_k = top_k
        self._vector_search_service = vector_search_service

    def search(self, query: str) -> list[MemorySearchResultItem]:
        normalized_query = query.strip().lower()

        logger.debug(
            "memory_search.started",
            {"query_len": len(normalized_query), "top_k": self._top_k},
        )

        if not normalized_query:
            logger.debug("memory_search.completed", {"result_count": 0})
            return []

        if self._vector_search_service is not None:
            vector_results = self._vector_search_service.search(normalized_query)
            if vector_results:
                logger.debug(
                    "memory_search.completed",
                    {"result_count": len(vector_results), "source": "vector"},
                )
                return vector_results

        user_model = self._user_model_repository.load()
        if user_model is None:
            logger.debug("memory_search.completed", {"result_count": 0})
            return []

        results = _search_user_model(user_model, normalized_query, self._top_k)
        logger.debug(
            "memory_search.completed",
            {"result_count": len(results), "source": "user_model"},
        )
        return results


def _search_user_model(
    user_model: UserModel,
    normalized_query: str,
    top_k: int,
) -> list[MemorySearchResultItem]:
    results: list[MemorySearchResultItem] = []

    for fact in user_model.facts:
        if normalized_query in fact.text.lower():
            results.append(
                MemorySearchResultItem(
                    id=fact.id,
                    source_type="fact",
                    text=fact.text,
                )
            )

    for preference in user_model.preferences:
        if normalized_query in preference.text.lower():
            results.append(
                MemorySearchResultItem(
                    id=preference.id,
                    source_type="preference",
                    text=preference.text,
                )
            )

    for constraint in user_model.constraints:
        if normalized_query in constraint.text.lower():
            results.append(
                MemorySearchResultItem(
                    id=constraint.id,
                    source_type="constraint",
                    text=constraint.text,
                )
            )

    return results[:top_k]
