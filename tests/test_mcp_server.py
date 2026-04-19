from __future__ import annotations

from pathlib import Path

import pytest

from seahorse.api.mcp_server import build_default_mcp_server, create_mcp_server
from seahorse.application.health_service import HealthService
from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.session_ingest_service import SessionIngestService
from seahorse.application.user_profile_merger import UserProfileMerger
from seahorse.application.user_profile_ingest_service import UserProfileIngestService
from seahorse.application.user_profile_renderer import UserProfileRenderer
from seahorse.bootstrap import SeahorseRuntime
from seahorse.domain.models import UserProfile, UserProfilePatch
from seahorse.infrastructure.config import (
    DEFAULT_CONFIG_FILE_NAME,
    USER_PROFILE_EXTRACTION_PROMPT_FILE_NAME,
)
from seahorse.tools.tool_names import (
    GET_USER_PROFILE_TOOL,
    INGEST_TURN_TOOL,
    SEARCH_MEMORY_TOOL,
)


class FakeUserModelRepository:
    def __init__(self, model: UserProfile | None = None) -> None:
        self.model = model

    def load(self) -> UserProfile | None:
        return self.model

    def save(self, model: UserProfile) -> None:
        self.model = model


class FakeExtractor:
    def extract(self, conversation, current_user_model) -> UserProfilePatch:
        return UserProfilePatch(
            summary="Prefers structured answers.",
            preferences_to_add=["Structured answers"],
        )


class FakeConversationVectorPipeline:
    def process(self, conversation) -> None:
        return None


class FakeVectorSearchService:
    def search(self, query: str):
        return []


def test_create_mcp_server_registers_expected_tools() -> None:
    user_model_repository = FakeUserModelRepository()
    session_ingest_service = SessionIngestService(
        UserProfileIngestService(
            user_model_repository=FakeUserModelRepository(),
            extractor=FakeExtractor(),
            merger=UserProfileMerger(),
        ),
        FakeConversationVectorPipeline(),
    )
    runtime = SeahorseRuntime(
        health_service=HealthService(),
        user_profile_repository=user_model_repository,
        memory_search_service=MemorySearchService(
            vector_search_service=FakeVectorSearchService()
        ),
        session_ingest_service=session_ingest_service,
        user_profile_renderer=UserProfileRenderer(),
        enabled_mcp_tools=frozenset(
            {
                GET_USER_PROFILE_TOOL,
                SEARCH_MEMORY_TOOL,
                INGEST_TURN_TOOL,
            }
        ),
    )

    server = create_mcp_server(runtime)

    manager = server._tool_manager  # noqa: SLF001
    assert manager is not None
    tools = {tool.name: tool for tool in manager.list_tools()}
    tool_names = set(tools)
    assert tool_names == {
        GET_USER_PROFILE_TOOL,
        SEARCH_MEMORY_TOOL,
        INGEST_TURN_TOOL,
    }
    assert "Returns what is known about the user" in tools[GET_USER_PROFILE_TOOL].description
    assert f"use {SEARCH_MEMORY_TOOL} instead" in tools[GET_USER_PROFILE_TOOL].description
    assert "vector similarity" in tools[SEARCH_MEMORY_TOOL].description
    assert "declarative phrase" in tools[SEARCH_MEMORY_TOOL].description
    assert "Persists new stable facts" in tools[INGEST_TURN_TOOL].description


def test_create_mcp_server_registers_only_enabled_tools() -> None:
    user_model_repository = FakeUserModelRepository()
    session_ingest_service = SessionIngestService(
        UserProfileIngestService(
            user_model_repository=FakeUserModelRepository(),
            extractor=FakeExtractor(),
            merger=UserProfileMerger(),
        ),
        FakeConversationVectorPipeline(),
    )
    runtime = SeahorseRuntime(
        health_service=HealthService(),
        user_profile_repository=user_model_repository,
        memory_search_service=MemorySearchService(
            vector_search_service=FakeVectorSearchService()
        ),
        session_ingest_service=session_ingest_service,
        user_profile_renderer=UserProfileRenderer(),
        enabled_mcp_tools=frozenset({SEARCH_MEMORY_TOOL}),
    )

    server = create_mcp_server(runtime)

    manager = server._tool_manager  # noqa: SLF001
    assert manager is not None
    tool_names = {tool.name for tool in manager.list_tools()}
    assert tool_names == {SEARCH_MEMORY_TOOL}


def test_build_default_mcp_server_requires_provider_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    prompt_dir = tmp_path / "src" / "seahorse" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / USER_PROFILE_EXTRACTION_PROMPT_FILE_NAME).write_text(
        "Return JSON.",
        encoding="utf-8",
    )
    (tmp_path / DEFAULT_CONFIG_FILE_NAME).write_text(
        (
            "provider:\n"
            "  model: openai/gpt-4.1-mini\n"
            "storage:\n"
            "  data_dir: data\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        build_default_mcp_server(tmp_path)
