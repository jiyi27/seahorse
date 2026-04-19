from __future__ import annotations

import pytest

from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.session_ingest_service import SessionIngestService
from seahorse.application.user_profile_merger import UserProfileMerger
from seahorse.application.user_profile_ingest_service import UserProfileIngestService
from seahorse.domain.models import (
    FactItem,
    MemorySearchResultItem,
    TextItem,
    UserProfile,
    UserProfilePatch,
)
from seahorse.tools.get_user_profile import get_user_profile
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.search_memory import search_memory
from seahorse.tools.tool_hints import (
    INGEST_RETRY_HINT,
    SEARCH_MEMORY_FAILED_HINT,
    search_memory_has_results_hint,
    SEARCH_MEMORY_NO_RESULTS_HINT,
    USER_PROFILE_EMPTY_HINT,
    USER_PROFILE_SUCCESS_HINT,
    USER_PROFILE_UNAVAILABLE_HINT,
)


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
            summary="Prefers direct answers.",
            preferences_to_add=["Direct answers"],
        )


class FakeConversationVectorPipeline:
    def process(self, conversation) -> None:
        return None


class FakeVectorSearchService:
    def __init__(self, results: list[MemorySearchResultItem] | None = None) -> None:
        self._results = results or []

    def search(self, query: str) -> list[MemorySearchResultItem]:
        return self._results


class FailingUserProfileRepository:
    def load(self) -> UserProfile | None:
        raise RuntimeError("User profile storage unavailable")

    def save(self, model: UserProfile) -> None:
        self.model = model


def build_session_ingest_service() -> SessionIngestService:
        return SessionIngestService(
            UserProfileIngestService(
                user_profile_repository=FakeUserProfileRepository(),
                extractor=FakeExtractor(),
                merger=UserProfileMerger(),
            ),
            FakeConversationVectorPipeline(),
        )


def build_user_profile() -> UserProfile:
    return UserProfile(
        summary="Prefers direct answers.",
        facts=[
            FactItem(
                id="fact_001",
                category="identity",
                text="User works best in the evening",
            )
        ],
        preferences=[TextItem(id="preference_001", text="Direct answers")],
        constraints=[TextItem(id="constraint_001", text="Dislikes being rushed")],
    )


def test_get_user_profile_returns_structured_profile() -> None:
    repository = FakeUserProfileRepository(build_user_profile())

    payload = get_user_profile(repository)

    assert payload == {
        "success": True,
        "profile": {
            "summary": "Prefers direct answers.",
            "facts": [
                {
                    "id": "fact_001",
                    "category": "identity",
                    "text": "User works best in the evening",
                }
            ],
            "preferences": [
                {
                    "id": "preference_001",
                    "text": "Direct answers",
                }
            ],
            "constraints": [
                {
                    "id": "constraint_001",
                    "text": "Dislikes being rushed",
                }
            ],
        },
        "hint": USER_PROFILE_SUCCESS_HINT,
    }


def test_get_user_profile_returns_null_when_user_profile_missing() -> None:
    repository = FakeUserProfileRepository()

    payload = get_user_profile(repository)

    assert payload == {
        "success": True,
        "profile": None,
        "hint": USER_PROFILE_EMPTY_HINT,
    }


def test_search_memory_returns_matching_results() -> None:
    service = MemorySearchService(
        vector_search_service=FakeVectorSearchService(
            [
                MemorySearchResultItem(
                    id="block_001",
                    source_type="conversation",
                    text="User works best at night",
                )
            ]
        )
    )

    payload = search_memory(service, query="rushed")

    assert payload == {
        "success": True,
        "results": [
            {
                "id": "block_001",
                "source_type": "conversation",
                "text": "User works best at night",
            }
        ],
        "hint": search_memory_has_results_hint(1),
    }


def test_search_memory_returns_empty_results_when_not_found() -> None:
    service = MemorySearchService(vector_search_service=FakeVectorSearchService())

    payload = search_memory(service, query="travel")

    assert payload == {
        "success": True,
        "results": [],
        "hint": SEARCH_MEMORY_NO_RESULTS_HINT,
    }


def test_ingest_turn_normalizes_messages_and_returns_result() -> None:
    service = build_session_ingest_service()

    payload = ingest_turn(
        service,
        messages=[{"role": "user", "text": "Please be direct."}],
    )

    assert payload["success"] is True
    assert payload["user_profile_updated"] is True


def test_get_user_profile_returns_structured_internal_error_on_runtime_failure() -> None:
    repository = FailingUserProfileRepository()

    payload = get_user_profile(repository)

    assert payload == {
        "success": False,
        "error_type": "internal_error",
        "message": "User profile storage unavailable",
        "hint": USER_PROFILE_UNAVAILABLE_HINT,
    }


def test_search_memory_returns_structured_internal_error_on_runtime_failure() -> None:
    service = MemorySearchService(
        vector_search_service=type(
            "FailingVectorSearchService",
            (),
            {
                "search": lambda self, query: (_ for _ in ()).throw(
                    RuntimeError("Vector search unavailable")
                )
            },
        )(),
    )

    payload = search_memory(service, query="night")

    assert payload == {
        "success": False,
        "error_type": "internal_error",
        "message": "Vector search unavailable",
        "hint": SEARCH_MEMORY_FAILED_HINT,
    }


def test_ingest_turn_returns_structured_internal_error_on_runtime_failure() -> None:
    service = build_session_ingest_service()

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
