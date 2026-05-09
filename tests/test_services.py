from __future__ import annotations

import pytest

from seahorse.application.session_ingest_service import SessionIngestService
from seahorse.application.user_profile_merger import UserProfileMerger
from seahorse.application.user_profile_ingest_service import UserProfileIngestService
from seahorse.domain.models import (
    ConversationInput,
    FactItem,
    FactPatchItem,
    Message,
    TextItem,
    UserProfile,
    UserProfilePatch,
)


class FakeUserProfileRepository:
    def __init__(self, model: UserProfile | None = None) -> None:
        self.model = model
        self.saved: list[UserProfile] = []

    def load(self) -> UserProfile | None:
        return self.model

    def save(self, model: UserProfile) -> None:
        self.model = model
        self.saved.append(model)


class FakeExtractor:
    def __init__(self, patch: UserProfilePatch) -> None:
        self.patch = patch
        self.calls = 0
        self.last_conversation: ConversationInput | None = None

    def extract(
        self,
        conversation: ConversationInput,
        current_user_profile: UserProfile | None,
    ) -> UserProfilePatch:
        self.calls += 1
        self.last_conversation = conversation
        return self.patch


class FakeConversationVectorPipeline:
    def __init__(self) -> None:
        self.calls = 0

    def process(self, conversation: ConversationInput) -> None:
        self.calls += 1


class FakeUserProfileIngestService:
    def __init__(self, result_updated: bool) -> None:
        self.calls = 0
        self.result_updated = result_updated

    def ingest(self, conversation: ConversationInput):
        self.calls += 1
        return type(
            "Result",
            (),
            {
                "user_profile_updated": self.result_updated,
            },
        )()


def test_user_profile_ingest_service_merges_and_persists_user_profile() -> None:
    user_profile_repo = FakeUserProfileRepository()
    extractor = FakeExtractor(
        UserProfilePatch(
            summary="The user prefers concise technical answers.",
            preferences_to_add=["Concise answers"],
            constraints_to_add=["Avoid unnecessary fluff"],
        )
    )
    service = UserProfileIngestService(
        user_profile_repository=user_profile_repo,
        extractor=extractor,
        merger=UserProfileMerger(),
    )

    result = service.ingest(
        ConversationInput(
            source="mcp",
            messages=[Message(role="user", text="Answer concisely.")],
        )
    )

    assert result.user_profile_updated is True
    assert [item.text for item in result.user_profile.preferences] == ["Concise answers"]
    assert [item.text for item in result.user_profile.constraints] == [
        "Avoid unnecessary fluff"
    ]
    assert extractor.calls == 1
    assert len(user_profile_repo.saved) == 1


def test_user_profile_ingest_service_reports_no_update_for_empty_initial_patch() -> None:
    user_profile_repo = FakeUserProfileRepository()
    extractor = FakeExtractor(UserProfilePatch())
    service = UserProfileIngestService(
        user_profile_repository=user_profile_repo,
        extractor=extractor,
        merger=UserProfileMerger(),
    )

    result = service.ingest(
        ConversationInput(
            source="mcp",
            messages=[Message(role="user", text="Hello there.")],
        )
    )

    assert result.user_profile_updated is False
    assert len(user_profile_repo.saved) == 0


def test_user_profile_ingest_service_ignores_non_user_messages() -> None:
    user_profile_repo = FakeUserProfileRepository()
    extractor = FakeExtractor(
        UserProfilePatch(preferences_to_add=["Concise answers"])
    )
    service = UserProfileIngestService(
        user_profile_repository=user_profile_repo,
        extractor=extractor,
        merger=UserProfileMerger(),
    )

    result = service.ingest(
        ConversationInput(
            source="mcp",
            messages=[
                Message(role="assistant", text="How should I respond?"),
                Message(role="user", text="Answer concisely."),
                Message(role="tool", text="metadata"),
            ],
        )
    )

    assert result.user_profile_updated is True
    assert extractor.calls == 1
    assert extractor.last_conversation.messages == [
        Message(role="user", text="Answer concisely.")
    ]


def test_user_profile_ingest_service_skips_extractor_without_user_messages() -> None:
    user_profile_repo = FakeUserProfileRepository()
    extractor = FakeExtractor(UserProfilePatch(preferences_to_add=["Concise answers"]))
    service = UserProfileIngestService(
        user_profile_repository=user_profile_repo,
        extractor=extractor,
        merger=UserProfileMerger(),
    )

    result = service.ingest(
        ConversationInput(
            source="mcp",
            messages=[Message(role="assistant", text="How should I respond?")],
        )
    )

    assert result.user_profile_updated is False
    assert extractor.calls == 0
    assert len(user_profile_repo.saved) == 0


def test_session_ingest_service_coordinates_user_profile_and_vector_pipeline() -> None:
    user_profile_ingest_service = FakeUserProfileIngestService(result_updated=True)
    conversation_vector_pipeline = FakeConversationVectorPipeline()
    service = SessionIngestService(
        user_profile_ingest_service,
        conversation_vector_pipeline,
    )

    result = service.ingest(
        ConversationInput(
            source="http",
            session_id="session-1",
            messages=[Message(role="user", text="Keep it concise.")],
        )
    )

    assert result.user_profile_updated is True
    assert result.vector_pipeline_processed is True
    assert user_profile_ingest_service.calls == 1
    assert conversation_vector_pipeline.calls == 1


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
    merger = UserProfileMerger()
    current = UserProfile(
        summary="Enjoys pragmatic answers.",
        facts=[
            FactItem(id="fact_001", category="identity", text="Uses Python"),
            FactItem(id="fact_002", category="life_situation", text="Works on agent systems"),
        ],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    merged = merger.merge(
        current,
        UserProfilePatch(
            summary="Enjoys pragmatic, concise answers.",
            facts_to_add=[
                FactPatchItem(category="life_situation", text="Builds memory systems"),
            ],
            fact_ids_to_remove=["fact_002"],
        ),
    )

    assert merged.changed is True
    assert merged.user_profile.summary == "Enjoys pragmatic, concise answers."
    assert merged.user_profile.facts == [
        FactItem(id="fact_001", category="identity", text="Uses Python"),
        FactItem(id="fact_002", category="life_situation", text="Builds memory systems"),
    ]


def test_merger_removes_only_target_section_items() -> None:
    merger = UserProfileMerger()
    current = UserProfile(
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
        UserProfilePatch(preference_ids_to_remove=["preference_001"]),
    )

    assert [item.text for item in merged.user_profile.facts] == ["Python", "Uses macOS"]
    assert [item.text for item in merged.user_profile.preferences] == ["Concise answers"]


def test_merger_preserves_existing_model_when_patch_is_empty() -> None:
    merger = UserProfileMerger()
    current = UserProfile(
        summary="First paragraph.\nSecond paragraph.",
        facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    merged = merger.merge(current, UserProfilePatch())

    assert merged.user_profile == current
    assert merged.changed is False


def test_merger_marks_new_empty_model_as_unchanged() -> None:
    merger = UserProfileMerger()

    merged = merger.merge(None, UserProfilePatch())

    assert merged.changed is False
    assert merged.user_profile == UserProfile()


def test_merger_marks_existing_model_unchanged_when_patch_addition_duplicates_active_text() -> None:
    merger = UserProfileMerger()
    current = UserProfile(
        summary="Keeps stable preferences.",
        facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    merged = merger.merge(
        current,
        UserProfilePatch(
            facts_to_add=[FactPatchItem(category="identity", text="Uses Python")]
        ),
    )

    assert merged.changed is False
    assert merged.user_profile == current
