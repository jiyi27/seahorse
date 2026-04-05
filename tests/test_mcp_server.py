from __future__ import annotations

from pathlib import Path

import pytest

from seahorse.api.mcp_server import build_default_mcp_server, create_mcp_server
from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.bootstrap import AppContainer
from seahorse.domain.models import CoreRule, UserModel, UserModelPatch


class FakeCoreRuleRepository:
    def __init__(self, model: CoreRule) -> None:
        self.model = model

    def load(self) -> CoreRule:
        return self.model


class FakeUserModelRepository:
    def __init__(self, model: UserModel | None = None) -> None:
        self.model = model

    def load(self) -> UserModel | None:
        return self.model

    def save(self, model: UserModel) -> None:
        self.model = model


class FakeExtractor:
    def extract(self, conversation, current_user_model, core_rule) -> UserModelPatch:
        return UserModelPatch(
            summary="Prefers structured answers.",
            preferences_to_add=["Structured answers"],
        )


class FakeEpisodePipeline:
    def process(self, conversation) -> None:
        return None


def test_create_mcp_server_registers_expected_tools() -> None:
    recall_service = RecallService(
        core_rule_repository=FakeCoreRuleRepository(CoreRule(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
    )
    ingest_service = IngestService(
        core_rule_repository=FakeCoreRuleRepository(CoreRule(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
        extractor=FakeExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )
    container = AppContainer(
        paths=None,  # type: ignore[arg-type]
        recall_service=recall_service,
        ingest_service=ingest_service,
    )

    server = create_mcp_server(container)

    manager = server._tool_manager  # noqa: SLF001
    assert manager is not None
    tool_names = {tool.name for tool in manager.list_tools()}
    assert "recall_context" in tool_names
    assert "ingest_turn" in tool_names


def test_build_default_mcp_server_requires_provider_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("SEAHORSE_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        build_default_mcp_server(tmp_path)
