from __future__ import annotations

from fastapi.testclient import TestClient

from seahorse.api.constants import HEALTH_PATH, MEMORY_CONTEXT_PATH, MEMORY_INGEST_PATH
from seahorse.api.http_server import create_http_app
from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.bootstrap import AppContainer
from seahorse.domain.models import Persona, UserModel, UserModelPatch


class FakePersonaRepository:
    def __init__(self, model: Persona) -> None:
        self.model = model

    def load(self) -> Persona:
        return self.model


class FakeUserModelRepository:
    def __init__(self, model: UserModel | None = None) -> None:
        self.model = model

    def load(self) -> UserModel | None:
        return self.model

    def save(self, model: UserModel) -> None:
        self.model = model


class FakeExtractor:
    def extract(self, conversation, current_user_model) -> UserModelPatch:
        return UserModelPatch(
            summary="Prefers concise answers.",
            preferences_to_add=["Concise answers"],
        )


class FakeEpisodePipeline:
    def process(self, conversation) -> None:
        return None


class FailingExtractor:
    def extract(self, conversation, current_user_model) -> UserModelPatch:
        raise RuntimeError("Extractor exploded")


def build_test_client() -> TestClient:
    recall_service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(
            UserModel(content="## Summary\n\nPrefers concise answers.\n")
        ),
    )
    ingest_service = IngestService(
        user_model_repository=FakeUserModelRepository(),
        extractor=FakeExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )
    container = AppContainer(
        recall_service=recall_service,
        ingest_service=ingest_service,
    )
    return TestClient(create_http_app(container))


def test_health_endpoint_returns_ok() -> None:
    client = build_test_client()

    response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_memory_context_endpoint_returns_stable_context() -> None:
    client = build_test_client()

    response = client.get(MEMORY_CONTEXT_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["persona"] == "Be precise."
    assert "Prefers concise answers." in payload["user_model"]


def test_memory_ingest_endpoint_updates_user_model() -> None:
    client = build_test_client()

    response = client.post(
        MEMORY_INGEST_PATH,
        json={
            "session_id": "session-1",
            "messages": [{"role": "user", "text": "Please be concise."}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["user_model_updated"] is True
    assert payload["version"] == 1
    assert "user_model" not in payload


def test_memory_ingest_endpoint_returns_structured_runtime_error() -> None:
    recall_service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
    )
    ingest_service = IngestService(
        user_model_repository=FakeUserModelRepository(),
        extractor=FailingExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )
    container = AppContainer(
        recall_service=recall_service,
        ingest_service=ingest_service,
    )
    client = TestClient(create_http_app(container), raise_server_exceptions=False)

    response = client.post(
        MEMORY_INGEST_PATH,
        json={
            "session_id": "session-1",
            "messages": [{"role": "user", "text": "Please be concise."}],
        },
    )

    assert response.status_code == 500
    assert response.headers["x-request-id"]
    assert response.json() == {
        "success": False,
        "error_type": "internal_error",
        "message": "Extractor exploded",
        "hint": (
            "An internal error occurred. Retry up to 2 times; if still failing, "
            "stop and notify the user with the message above."
        ),
    }


def test_memory_ingest_endpoint_returns_structured_validation_error() -> None:
    client = build_test_client()

    response = client.post(MEMORY_INGEST_PATH, json={})

    assert response.status_code == 422
    assert response.headers["x-request-id"]
    assert response.json() == {
        "error": "Invalid request payload",
        "type": "ValidationError",
    }


def test_memory_context_endpoint_returns_null_when_user_model_missing() -> None:
    recall_service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
    )
    ingest_service = IngestService(
        user_model_repository=FakeUserModelRepository(),
        extractor=FakeExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )
    container = AppContainer(
        recall_service=recall_service,
        ingest_service=ingest_service,
    )
    client = TestClient(create_http_app(container))

    response = client.get(MEMORY_CONTEXT_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "persona": "Be precise.",
        "user_model": None,
    }
