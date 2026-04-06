from __future__ import annotations

import pytest

from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.domain.models import CoreRule, UserModel, UserModelPatch
from seahorse.tools.contracts import INGEST_RETRY_HINT, RECALL_CONTEXT_UNAVAILABLE_HINT
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.recall_context import recall_context


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
            summary="Prefers direct answers.",
            preferences_to_add=["Direct answers"],
        )


class FakeEpisodePipeline:
    def process(self, conversation) -> None:
        return None


class FailingCoreRuleRepository:
    def load(self) -> CoreRule:
        raise RuntimeError("Core rule storage unavailable")


def test_recall_context_returns_string_payload() -> None:
    service = RecallService(
        core_rule_repository=FakeCoreRuleRepository(CoreRule(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(
            UserModel(content="## Summary\n\nPrefers direct answers.\n")
        ),
    )

    payload = recall_context(service)

    assert payload["success"] is True
    assert payload["core_rule"] == "Be precise."
    assert "Prefers direct answers." in payload["user_model"]


def test_recall_context_returns_none_when_user_model_missing() -> None:
    service = RecallService(
        core_rule_repository=FakeCoreRuleRepository(CoreRule(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
    )

    payload = recall_context(service)

    assert payload == {
        "success": True,
        "core_rule": "Be precise.",
        "user_model": None,
    }


def test_ingest_turn_normalizes_messages_and_returns_result() -> None:
    service = IngestService(
        core_rule_repository=FakeCoreRuleRepository(CoreRule(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
        extractor=FakeExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )

    payload = ingest_turn(
        service,
        messages=[{"role": "user", "text": "Please be direct."}],
    )

    assert payload["success"] is True
    assert payload["user_model_updated"] is True
    assert payload["version"] == 1


def test_recall_context_returns_structured_internal_error_on_runtime_failure() -> None:
    service = RecallService(
        core_rule_repository=FailingCoreRuleRepository(),
        user_model_repository=FakeUserModelRepository(),
    )

    payload = recall_context(service)

    assert payload == {
        "success": False,
        "error_type": "internal_error",
        "message": "Core rule storage unavailable",
        "hint": RECALL_CONTEXT_UNAVAILABLE_HINT,
    }


def test_ingest_turn_returns_structured_internal_error_on_runtime_failure() -> None:
    service = IngestService(
        core_rule_repository=FakeCoreRuleRepository(CoreRule(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
        extractor=FakeExtractor(),
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            service,
            "ingest",
            lambda conversation: (_ for _ in ()).throw(RuntimeError("Extractor exploded")),
        )
        payload = ingest_turn(
            service,
            messages=[{"role": "user", "text": "Please be direct."}],
        )

    assert payload == {
        "success": False,
        "error_type": "internal_error",
        "message": "Extractor exploded",
        "hint": INGEST_RETRY_HINT,
    }
