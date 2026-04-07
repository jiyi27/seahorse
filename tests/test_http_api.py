from __future__ import annotations

from fastapi.testclient import TestClient

from seahorse.api.constants import (
    HEALTH_PATH,
    MEMORY_INGEST_PATH,
    MEMORY_SEARCH_PATH,
    PERSONA_PATH,
    USER_PROFILE_PATH,
)
from seahorse.api.http_server import create_http_app
from seahorse.application.ingest_service import IngestService
from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.application.user_model_renderer import UserModelRenderer
from seahorse.bootstrap import AppContainer
from seahorse.domain.models import FactItem, Persona, TextItem, UserModel, UserModelPatch
from seahorse.tools.tool_hints import PERSONA_SUCCESS_HINT, USER_PROFILE_SUCCESS_HINT
from seahorse.tools.tool_names import GET_PERSONA_TOOL, GET_USER_PROFILE_TOOL, INGEST_TURN_TOOL, SEARCH_MEMORY_TOOL


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


def build_user_model() -> UserModel:
    return UserModel(
        summary="Prefers concise answers.",
        facts=[
            FactItem(
                id="fact_001",
                category="identity",
                text="User works best at night",
            )
        ],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )


def build_test_client() -> TestClient:
    user_model_repository = FakeUserModelRepository(build_user_model())
    recall_service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=user_model_repository,
    )
    ingest_service = IngestService(
        user_model_repository=FakeUserModelRepository(),
        extractor=FakeExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )
    container = AppContainer(
        recall_service=recall_service,
        memory_search_service=MemorySearchService(user_model_repository),
        ingest_service=ingest_service,
        user_model_renderer=UserModelRenderer(),
        enabled_mcp_tools=frozenset(
            {
                GET_PERSONA_TOOL,
                GET_USER_PROFILE_TOOL,
                SEARCH_MEMORY_TOOL,
                INGEST_TURN_TOOL,
            }
        ),
    )
    return TestClient(create_http_app(container))


def test_health_endpoint_returns_ok() -> None:
    client = build_test_client()

    response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_persona_endpoint_returns_persona() -> None:
    client = build_test_client()

    response = client.get(PERSONA_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "content": "Be precise.",
        "hint": PERSONA_SUCCESS_HINT,
    }


def test_user_profile_endpoint_returns_structured_profile() -> None:
    client = build_test_client()

    response = client.get(USER_PROFILE_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["profile"]["summary"] == "Prefers concise answers."
    assert payload["profile"]["preferences"][0]["text"] == "Concise answers"
    assert payload["hint"] == USER_PROFILE_SUCCESS_HINT


def test_memory_search_endpoint_returns_matches() -> None:
    client = build_test_client()

    response = client.get(MEMORY_SEARCH_PATH, params={"query": "night"})

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "results": [
            {
                "id": "fact_001",
                "source_type": "fact",
                "text": "User works best at night",
            }
        ],
        "hint": (
            "These may or may not be what you're looking for - treat them as loose "
            "leads, not confirmed facts. If something looks relevant, bring it up "
            "naturally rather than announcing a search result. If you're unsure, "
            "ask casually. If two attempts don't land, let it go - tell the user "
            "you can't quite place it and move on."
        ),
    }


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
    assert "user_model" not in payload


def test_memory_ingest_endpoint_returns_structured_runtime_error() -> None:
    user_model_repository = FakeUserModelRepository()
    recall_service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=user_model_repository,
    )
    ingest_service = IngestService(
        user_model_repository=FakeUserModelRepository(),
        extractor=FailingExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )
    container = AppContainer(
        recall_service=recall_service,
        memory_search_service=MemorySearchService(user_model_repository),
        ingest_service=ingest_service,
        user_model_renderer=UserModelRenderer(),
        enabled_mcp_tools=frozenset(
            {
                GET_PERSONA_TOOL,
                GET_USER_PROFILE_TOOL,
                SEARCH_MEMORY_TOOL,
                INGEST_TURN_TOOL,
            }
        ),
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


def test_memory_search_endpoint_rejects_invalid_query() -> None:
    client = build_test_client()

    response = client.get(MEMORY_SEARCH_PATH, params={"query": ""})

    assert response.status_code == 422
    assert response.headers["x-request-id"]
    assert response.json() == {
        "error": "Invalid request payload",
        "type": "RequestValidationError",
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


def test_memory_ingest_endpoint_rejects_content_and_messages_together() -> None:
    client = build_test_client()

    response = client.post(
        MEMORY_INGEST_PATH,
        json={
            "content": "Please be concise.",
            "messages": [{"role": "user", "text": "Please be concise."}],
        },
    )

    assert response.status_code == 422
    assert response.headers["x-request-id"]
    assert response.json() == {
        "error": "Invalid request payload",
        "type": "ValidationError",
    }


def test_user_profile_endpoint_returns_null_when_user_model_missing() -> None:
    user_model_repository = FakeUserModelRepository()
    recall_service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=user_model_repository,
    )
    ingest_service = IngestService(
        user_model_repository=FakeUserModelRepository(),
        extractor=FakeExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )
    container = AppContainer(
        recall_service=recall_service,
        memory_search_service=MemorySearchService(user_model_repository),
        ingest_service=ingest_service,
        user_model_renderer=UserModelRenderer(),
        enabled_mcp_tools=frozenset(
            {
                GET_PERSONA_TOOL,
                GET_USER_PROFILE_TOOL,
                SEARCH_MEMORY_TOOL,
                INGEST_TURN_TOOL,
            }
        ),
    )
    client = TestClient(create_http_app(container))

    response = client.get(USER_PROFILE_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "profile": None,
        "hint": "No user profile has been built yet. Proceed without personalization.",
    }
