from __future__ import annotations

from seahorse.application.health_service import HealthService
from seahorse.retrieval.vector_health_service import VectorHealthService


class HealthyEmbeddingModel:
    def check_connection(self) -> None:
        return None


class HealthyVectorStore:
    def check_connection(self) -> None:
        return None


class FailingVectorStore:
    def check_connection(self) -> None:
        raise RuntimeError("qdrant unavailable")


def test_health_service_reports_vector_memory_disabled_by_default() -> None:
    service = HealthService()

    assert service.check() == {
        "status": "ok",
        "checks": {
            "api": "ok",
            "vector_memory": "disabled",
        },
    }


def test_vector_health_service_reports_ok_when_dependencies_are_reachable() -> None:
    service = VectorHealthService(HealthyEmbeddingModel(), HealthyVectorStore())

    assert service.check() == {
        "embedding": "ok",
        "qdrant": "ok",
    }


def test_health_service_reports_degraded_when_vector_dependency_fails() -> None:
    service = HealthService(
        vector_health_service=VectorHealthService(
            HealthyEmbeddingModel(),
            FailingVectorStore(),
        )
    )

    assert service.check() == {
        "status": "degraded",
        "checks": {
            "api": "ok",
            "embedding": "ok",
            "qdrant": "error: RuntimeError",
        },
    }
