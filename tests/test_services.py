from __future__ import annotations

import pytest

from seahorse.application.ingest_service import IngestService
from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.domain.models import (
    ConversationInput,
    FactItem,
    FactPatchItem,
    Message,
    Persona,
    TextItem,
    UserModel,
    UserModelPatch,
)


class FakePersonaRepository:
    def __init__(self, model: Persona) -> None:
        self.model = model

    def load(self) -> Persona:
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
    ) -> UserModelPatch:
        self.calls += 1
        return self.patch


class FakeEpisodePipeline:
    def __init__(self) -> None:
        self.calls = 0

    def process(self, conversation: ConversationInput) -> None:
        self.calls += 1


def test_recall_service_returns_persona_and_user_model() -> None:
    persona_repo = FakePersonaRepository(Persona(content="Be precise."))
    user_model_repo = FakeUserModelRepository(
        UserModel(
            summary="Knows Python.",
            facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
        )
    )

    service = RecallService(persona_repo, user_model_repo)
    persona = service.get_persona()
    user_model = service.get_user_model()

    assert persona.content == "Be precise."
    assert user_model is not None
    assert user_model.summary == "Knows Python."


def test_memory_search_service_returns_matching_items() -> None:
    user_model_repo = FakeUserModelRepository(
        UserModel(
            facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
            preferences=[TextItem(id="preference_001", text="Prefers concise answers")],
        )
    )

    service = MemorySearchService(user_model_repo)
    results = service.search("python")

    assert [result.model_dump() for result in results] == [
        {
            "id": "fact_001",
            "source_type": "fact",
            "text": "Uses Python",
        }
    ]


def test_ingest_service_merges_and_persists_user_model() -> None:
    user_model_repo = FakeUserModelRepository()
    extractor = FakeExtractor(
        UserModelPatch(
            summary="The user prefers concise technical answers.",
            preferences_to_add=["Concise answers"],
            constraints_to_add=["Avoid unnecessary fluff"],
        )
    )
    service = IngestService(
        user_model_repository=user_model_repo,
        extractor=extractor,
        merger=UserModelMerger(),
        episode_pipeline=FakeEpisodePipeline(),
    )

    result = service.ingest(
        ConversationInput(
            source="mcp",
            messages=[Message(role="user", text="Answer concisely.")],
        )
    )

    assert result.user_model_updated is True
    assert [item.text for item in result.user_model.preferences] == ["Concise answers"]
    assert [item.text for item in result.user_model.constraints] == [
        "Avoid unnecessary fluff"
    ]
    assert extractor.calls == 1
    assert len(user_model_repo.saved) == 1


def test_ingest_service_reports_no_update_for_empty_initial_patch() -> None:
    user_model_repo = FakeUserModelRepository()
    extractor = FakeExtractor(UserModelPatch())
    episode_pipeline = FakeEpisodePipeline()
    service = IngestService(
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
    assert len(user_model_repo.saved) == 0
    assert episode_pipeline.calls == 1


def test_conversation_input_normalizes_blank_content_when_messages_are_present() -> None:
    conversation = ConversationInput(
        source="mcp",
        content="   ",
        messages=[Message(role="user", text="Keep responses concise.")],
    )

    assert conversation.content is None
    assert conversation.messages == [Message(role="user", text="Keep responses concise.")]


def test_conversation_input_rejects_content_and_messages_together() -> None:
    with pytest.raises(ValueError, match="either content or messages, not both"):
        ConversationInput(
            source="http",
            content="Keep responses concise.",
            messages=[Message(role="user", text="Keep responses concise.")],
        )


def test_merger_replaces_fact_by_id_and_keeps_category() -> None:
    merger = UserModelMerger()
    current = UserModel(
        summary="Enjoys pragmatic answers.",
        facts=[
            FactItem(id="fact_001", category="identity", text="Uses Python"),
            FactItem(id="fact_002", category="life_situation", text="Works on agent systems"),
        ],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    merged = merger.merge(
        current,
        UserModelPatch(
            summary="Enjoys pragmatic, concise answers.",
            facts_to_add=[
                FactPatchItem(category="life_situation", text="Builds memory systems"),
            ],
            fact_ids_to_remove=["fact_002"],
        ),
    )

    assert merged.changed is True
    assert merged.user_model.summary == "Enjoys pragmatic, concise answers."
    assert merged.user_model.facts == [
        FactItem(id="fact_001", category="identity", text="Uses Python"),
        FactItem(id="fact_002", category="life_situation", text="Builds memory systems"),
    ]


def test_merger_removes_only_target_section_items() -> None:
    merger = UserModelMerger()
    current = UserModel(
        summary="Tracks stable user preferences.",
        facts=[
            FactItem(id="fact_001", category="identity", text="Python"),
            FactItem(id="fact_002", category="identity", text="Uses macOS"),
        ],
        preferences=[
            TextItem(id="preference_001", text="Python"),
            TextItem(id="preference_002", text="Concise answers"),
        ],
    )

    merged = merger.merge(
        current,
        UserModelPatch(preference_ids_to_remove=["preference_001"]),
    )

    assert [item.text for item in merged.user_model.facts] == ["Python", "Uses macOS"]
    assert [item.text for item in merged.user_model.preferences] == ["Concise answers"]


def test_merger_preserves_existing_model_when_patch_is_empty() -> None:
    merger = UserModelMerger()
    current = UserModel(
        summary="First paragraph.\nSecond paragraph.",
        facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    merged = merger.merge(current, UserModelPatch())

    assert merged.user_model == current
    assert merged.changed is False


def test_merger_marks_new_empty_model_as_unchanged() -> None:
    merger = UserModelMerger()

    merged = merger.merge(None, UserModelPatch())

    assert merged.changed is False
    assert merged.user_model == UserModel()


def test_merger_marks_existing_model_unchanged_when_patch_addition_duplicates_active_text() -> None:
    merger = UserModelMerger()
    current = UserModel(
        summary="Keeps stable preferences.",
        facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    merged = merger.merge(
        current,
        UserModelPatch(
            facts_to_add=[FactPatchItem(category="identity", text="Uses Python")]
        ),
    )

    assert merged.changed is False
    assert merged.user_model == current
