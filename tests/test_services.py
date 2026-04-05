from __future__ import annotations

from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.domain.models import (
    ConversationInput,
    CoreRule,
    Message,
    UserModel,
    UserModelPatch,
)


class FakeCoreRuleRepository:
    def __init__(self, model: CoreRule) -> None:
        self.model = model

    def load(self) -> CoreRule:
        return self.model


class FakeUserModelRepository:
    def __init__(self, model: UserModel | None = None) -> None:
        self.model = model
        self.saved: list[UserModel] = []

    def load(self) -> UserModel | None:
        return self.model

    def save(self, model: UserModel) -> None:
        self.model = model
        self.saved.append(model)


class FakeExtractor:
    def __init__(self, patch: UserModelPatch) -> None:
        self.patch = patch
        self.calls = 0

    def extract(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
        core_rule: CoreRule,
    ) -> UserModelPatch:
        self.calls += 1
        return self.patch


class FakeEpisodePipeline:
    def __init__(self) -> None:
        self.calls = 0
        self.payloads: list[ConversationInput] = []

    def process(self, conversation: ConversationInput) -> None:
        self.calls += 1
        self.payloads.append(conversation)


def test_recall_service_returns_core_rule_and_user_model() -> None:
    core_rule_repo = FakeCoreRuleRepository(CoreRule(content="Be precise."))
    user_model_repo = FakeUserModelRepository(UserModel(content="## Summary\n\nKnows Python.\n"))

    service = RecallService(core_rule_repo, user_model_repo)
    result = service.recall()

    assert result.core_rule.content == "Be precise."
    assert result.user_model is not None
    assert "Knows Python." in result.user_model.content


def test_ingest_service_merges_and_persists_user_model() -> None:
    core_rule_repo = FakeCoreRuleRepository(CoreRule(content="Be precise."))
    user_model_repo = FakeUserModelRepository()
    extractor = FakeExtractor(
        UserModelPatch(
            summary="The user prefers concise technical answers.",
            preferences_to_add=["Concise answers"],
            preferences_to_remove=[],
            constraints_to_add=["Avoid unnecessary fluff"],
        )
    )
    episode_pipeline = FakeEpisodePipeline()
    service = IngestService(
        core_rule_repository=core_rule_repo,
        user_model_repository=user_model_repo,
        extractor=extractor,
        merger=UserModelMerger(),
        episode_pipeline=episode_pipeline,
    )

    result = service.ingest(
        ConversationInput(
            source="mcp",
            messages=[Message(role="user", text="Answer concisely.")],
        )
    )

    assert result.user_model_updated is True
    assert result.user_model.version == 1
    assert "Concise answers" in result.user_model.content
    assert "Avoid unnecessary fluff" in result.user_model.content
    assert extractor.calls == 1
    assert len(user_model_repo.saved) == 1
    assert episode_pipeline.calls == 1


def test_ingest_service_reports_no_update_for_empty_initial_patch() -> None:
    core_rule_repo = FakeCoreRuleRepository(CoreRule(content="Be precise."))
    user_model_repo = FakeUserModelRepository()
    extractor = FakeExtractor(UserModelPatch())
    episode_pipeline = FakeEpisodePipeline()
    service = IngestService(
        core_rule_repository=core_rule_repo,
        user_model_repository=user_model_repo,
        extractor=extractor,
        merger=UserModelMerger(),
        episode_pipeline=episode_pipeline,
    )

    result = service.ingest(
        ConversationInput(
            source="mcp",
            messages=[Message(role="user", text="Hello there.")],
        )
    )

    assert result.user_model_updated is False
    assert result.user_model.version == 1
    assert len(user_model_repo.saved) == 1
    assert episode_pipeline.calls == 1


def test_merger_keeps_output_deterministic_and_removes_stale_items() -> None:
    merger = UserModelMerger()
    current = UserModel(
        content=(
            "## Summary\n\nEnjoys pragmatic answers.\n\n"
            "## Facts\n\n- Uses Python\n- Works on agent systems\n\n"
            "## Preferences\n\n- Concise answers\n\n"
            "## Constraints\n\n- None\n"
        )
    )

    merged = merger.merge(
        current,
        UserModelPatch(
            summary="Enjoys pragmatic, concise answers.",
            facts_to_add=["Uses Python", "Builds memory systems"],
            facts_to_remove=["Works on agent systems"],
        ),
    )

    assert merged.changed is True
    assert "Enjoys pragmatic, concise answers." in merged.user_model.content
    assert "- Uses Python" in merged.user_model.content
    assert "- Builds memory systems" in merged.user_model.content
    assert "Works on agent systems" not in merged.user_model.content
    assert merged.user_model.version == current.version + 1


def test_merger_removes_only_target_section_items() -> None:
    merger = UserModelMerger()
    current = UserModel(
        content=(
            "## Summary\n\nTracks stable user preferences.\n\n"
            "## Facts\n\n- Python\n- Uses macOS\n\n"
            "## Preferences\n\n- Python\n- Concise answers\n\n"
            "## Constraints\n\n- None\n"
        )
    )

    merged = merger.merge(
        current,
        UserModelPatch(
            preferences_to_remove=["Python"],
        ),
    )

    assert "- Python" in merged.user_model.content
    assert "## Facts\n\n- Python\n- Uses macOS" in merged.user_model.content
    assert "## Preferences\n\n- Concise answers" in merged.user_model.content


def test_merger_preserves_multiline_summary() -> None:
    merger = UserModelMerger()
    current = UserModel(
        content=(
            "## Summary\n\nFirst paragraph.\nSecond paragraph.\n\n"
            "## Facts\n\n- Uses Python\n\n"
            "## Preferences\n\n- Concise answers\n\n"
            "## Constraints\n\n- None\n"
        )
    )

    merged = merger.merge(current, UserModelPatch())

    assert "## Summary\n\nFirst paragraph.\nSecond paragraph." in merged.user_model.content
