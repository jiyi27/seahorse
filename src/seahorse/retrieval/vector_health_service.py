from __future__ import annotations

from seahorse import logger


class VectorHealthService:
    def __init__(self, embedding_model, vector_store) -> None:
        self._embedding_model = embedding_model
        self._vector_store = vector_store

    def check(self) -> dict[str, str]:
        checks = {
            "embedding": self._check_embedding(),
            "qdrant": self._check_qdrant(),
        }
        return checks

    def _check_embedding(self) -> str:
        try:
            self._embedding_model.check_connection()
        except Exception as exc:
            logger.warning(
                "vector_health.embedding.failed",
                {"error": str(exc)},
                exc=exc,
            )
            return f"error: {type(exc).__name__}"
        return "ok"

    def _check_qdrant(self) -> str:
        try:
            self._vector_store.check_connection()
        except Exception as exc:
            logger.warning(
                "vector_health.qdrant.failed",
                {"error": str(exc)},
                exc=exc,
            )
            return f"error: {type(exc).__name__}"
        return "ok"
