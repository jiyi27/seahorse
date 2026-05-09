from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from seahorse import logger

from seahorse.api.constants import (
    HEALTH_PATH,
    MEMORY_INGEST_PATH,
)
from seahorse.api.http_errors import register_http_exception_handlers
from seahorse.api.http_logging import register_http_logging_middleware
from seahorse.api.http_server import create_http_app
from seahorse.application.health_service import HealthService
from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.session_ingest_service import SessionIngestService
from seahorse.application.user_profile_merger import UserProfileMerger
from seahorse.application.user_profile_ingest_service import UserProfileIngestService
from seahorse.bootstrap import SeahorseRuntime
from seahorse.domain.models import (
    MemorySearchResultItem,
    UserProfile,
    UserProfilePatch,
)
from seahorse.tools.tool_names import GET_USER_PROFILE_TOOL, INGEST_TURN_TOOL, SEARCH_MEMORY_TOOL


class FakeUserProfileRepository:
    def __init__(self, model: UserProfile | None = None) -> None:
        self.model = model

    def load(self) -> UserProfile | None:
        return self.model

    def save(self, model: UserProfile) -> None:
        self.model = model


class FakeExtractor:
    def extract(self, conversation, current_user_profile) -> UserProfilePatch:
        return UserProfilePatch(
            summary="Prefers concise answers.",
            preferences_to_add=["Concise answers"],
        )


class FakeConversationVectorPipeline:
    def process(self, conversation) -> None:
        return None


class FakeVectorSearchService:
    def search(self, query: str) -> list[MemorySearchResultItem]:
        return [
            MemorySearchResultItem(
                id="block_001",
                source_type="conversation",
                text="User works best at night",
            )
        ]


class FailingExtractor:
    def extract(self, conversation, current_user_profile) -> UserProfilePatch:
        raise RuntimeError("Extractor exploded")


def build_test_client() -> TestClient:
    session_ingest_service = SessionIngestService(
        UserProfileIngestService(
            user_profile_repository=FakeUserProfileRepository(),
            extractor=FakeExtractor(),
            merger=UserProfileMerger(),
        ),
        FakeConversationVectorPipeline(),
    )
    runtime = SeahorseRuntime(
        health_service=HealthService(),
        user_profile_repository=FakeUserProfileRepository(),
        memory_search_service=MemorySearchService(
            vector_search_service=FakeVectorSearchService()
        ),
        session_ingest_service=session_ingest_service,
        enabled_mcp_tools=frozenset(
            {
                GET_USER_PROFILE_TOOL,
                SEARCH_MEMORY_TOOL,
                INGEST_TURN_TOOL,
            }
        ),
    )
    return TestClient(create_http_app(runtime))


def _read_info_log_records(log_dir: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(log_dir.glob("*.info.log")):
        for line in path.read_text(encoding="utf-8").splitlines():
            records.append(json.loads(line))
    return records


def test_health_endpoint_returns_ok() -> None:
    client = build_test_client()

    response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "api": "ok",
            "vector_memory": "disabled",
        },
    }


def test_memory_ingest_endpoint_updates_user_profile() -> None:
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
    assert payload["user_profile_updated"] is True
    assert "user_profile" not in payload


def test_http_middleware_logs_request_and_response_bodies(tmp_path: Path) -> None:
    logger.configure(log_dir=tmp_path, level="info")
    client = build_test_client()

    response = client.post(
        MEMORY_INGEST_PATH,
        headers={"X-Request-Id": "req-1234"},
        json={
            "session_id": "session-1",
            "messages": [{"role": "user", "text": "Please be concise."}],
        },
    )

    assert response.status_code == 200

    records = _read_info_log_records(tmp_path)
    request_record = next(
        record for record in records if record["topic"] == "http.request.in"
    )
    response_record = next(
        record for record in records if record["topic"] == "http.response.out"
    )

    assert request_record["context_id"] == "req-1234"
    assert request_record["data"] == {
        "method": "POST",
        "path": MEMORY_INGEST_PATH,
        "query": {},
        "body": {
            "session_id": "session-1",
            "messages": [{"role": "user", "text": "Please be concise."}],
        },
    }
    assert response_record["context_id"] == "req-1234"
    assert response_record["data"]["method"] == "POST"
    assert response_record["data"]["path"] == MEMORY_INGEST_PATH
    assert response_record["data"]["status_code"] == 200
    assert response_record["data"]["body"] == {
        "success": True,
        "user_profile_updated": True,
    }


def test_memory_ingest_endpoint_returns_structured_runtime_error() -> None:
    user_profile_repository = FakeUserProfileRepository()
    session_ingest_service = SessionIngestService(
        UserProfileIngestService(
            user_profile_repository=FakeUserProfileRepository(),
            extractor=FailingExtractor(),
            merger=UserProfileMerger(),
        ),
        FakeConversationVectorPipeline(),
    )
    runtime = SeahorseRuntime(
        health_service=HealthService(),
        user_profile_repository=user_profile_repository,
        memory_search_service=MemorySearchService(
            vector_search_service=FakeVectorSearchService()
        ),
        session_ingest_service=session_ingest_service,
        enabled_mcp_tools=frozenset(
            {
                GET_USER_PROFILE_TOOL,
                SEARCH_MEMORY_TOOL,
                INGEST_TURN_TOOL,
            }
        ),
    )
    client = TestClient(create_http_app(runtime), raise_server_exceptions=False)

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


def test_unhandled_http_exception_returns_generic_error_with_request_id() -> None:
    app = FastAPI()
    register_http_logging_middleware(app)
    register_http_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise ValueError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom", headers={"X-Request-Id": "req-boom"})

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "req-boom"
    assert response.json() == {
        "error": "Internal server error",
        "type": "ValueError",
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
