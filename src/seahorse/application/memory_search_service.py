from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import MemorySearchResultItem, UserModel
from seahorse.domain.repositories import UserModelRepository

DEFAULT_TOP_K = 3
MAX_TOP_K = 10


class MemorySearchService:
    def __init__(self, user_model_repository: UserModelRepository) -> None:
        self._user_model_repository = user_model_repository

    def search(self, query: str, *, top_k: int = DEFAULT_TOP_K) -> list[MemorySearchResultItem]:
        normalized_query = query.strip().lower()
        bounded_top_k = max(1, min(top_k, MAX_TOP_K))

        logger.debug(
            "memory_search.started",
            {"query_len": len(normalized_query), "top_k": bounded_top_k},
        )

        if not normalized_query:
            logger.debug("memory_search.completed", {"result_count": 0})
            return []

        user_model = self._user_model_repository.load()
        if user_model is None:
            logger.debug("memory_search.completed", {"result_count": 0})
            return []

        results = _search_user_model(user_model, normalized_query, bounded_top_k)
        logger.debug("memory_search.completed", {"result_count": len(results)})
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
