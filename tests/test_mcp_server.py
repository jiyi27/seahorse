from __future__ import annotations

from pathlib import Path

import pytest

from seahorse.api.mcp_server import build_default_mcp_server, create_mcp_server
from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.bootstrap import AppContainer
from seahorse.domain.models import Persona, UserModel, UserModelPatch
from seahorse.infrastructure.config import (
    DEFAULT_CONFIG_FILE_NAME,
    USER_MODEL_EXTRACTION_PROMPT_FILE_NAME,
)


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
            summary="Prefers structured answers.",
            preferences_to_add=["Structured answers"],
        )


class FakeEpisodePipeline:
    def process(self, conversation) -> None:
        return None


def test_create_mcp_server_registers_expected_tools() -> None:
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

    server = create_mcp_server(container)

    manager = server._tool_manager  # noqa: SLF001
    assert manager is not None
    tools = {tool.name: tool for tool in manager.list_tools()}
    tool_names = set(tools)
    assert "recall_context" in tool_names
    assert "ingest_turn" in tool_names
    assert "Returns the user's persistent memory context" in tools["recall_context"].description
    assert "start of every session" in tools["recall_context"].description
    assert "Persists new stable facts" in tools["ingest_turn"].description
    assert "end of a session" in tools["ingest_turn"].description


def test_build_default_mcp_server_requires_provider_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    prompt_dir = tmp_path / "src" / "seahorse" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME).write_text(
        "Return JSON.",
        encoding="utf-8",
    )
    persona_dir = tmp_path / "personas"
    persona_dir.mkdir(parents=True)
    (persona_dir / "default.md").write_text("# Core Rule\n\nBe precise.\n", encoding="utf-8")
    (tmp_path / DEFAULT_CONFIG_FILE_NAME).write_text(
        (
            "provider:\n"
            "  model: openai/gpt-4.1-mini\n"
            "storage:\n"
            "  data_dir: data\n"
            "  persona_dir: personas\n"
            "  persona_name: default\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        build_default_mcp_server(tmp_path)
