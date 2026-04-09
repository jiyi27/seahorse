from __future__ import annotations

import pytest

from seahorse.application.ingest_service import IngestService
from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.domain.models import FactItem, TextItem, UserModel, UserModelPatch
from seahorse.tools.get_user_profile import get_user_profile
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.search_memory import search_memory
from seahorse.tools.tool_hints import (
    INGEST_RETRY_HINT,
    SEARCH_MEMORY_FAILED_HINT,
    SEARCH_MEMORY_HAS_RESULTS_HINT,
    SEARCH_MEMORY_NO_RESULTS_HINT,
    USER_PROFILE_EMPTY_HINT,
    USER_PROFILE_SUCCESS_HINT,
    USER_PROFILE_UNAVAILABLE_HINT,
)


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
            summary="Prefers direct answers.",
            preferences_to_add=["Direct answers"],
        )


class FakeEpisodePipeline:
    def process(self, conversation) -> None:
        return None


class FailingUserModelRepository:
    def load(self) -> UserModel | None:
        raise RuntimeError("User model storage unavailable")

    def save(self, model: UserModel) -> None:
        self.model = model


def build_user_model() -> UserModel:
    return UserModel(
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
    service = RecallService(FakeUserModelRepository(build_user_model()))

    payload = get_user_profile(service)

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


def test_get_user_profile_returns_null_when_user_model_missing() -> None:
    service = RecallService(FakeUserModelRepository())

    payload = get_user_profile(service)

    assert payload == {
        "success": True,
        "profile": None,
        "hint": USER_PROFILE_EMPTY_HINT,
    }


def test_search_memory_returns_matching_results() -> None:
    service = MemorySearchService(FakeUserModelRepository(build_user_model()))

    payload = search_memory(service, query="rushed")

    assert payload == {
        "success": True,
        "results": [
            {
                "id": "constraint_001",
                "source_type": "constraint",
                "text": "Dislikes being rushed",
            }
        ],
        "hint": SEARCH_MEMORY_HAS_RESULTS_HINT,
    }


def test_search_memory_returns_empty_results_when_not_found() -> None:
    service = MemorySearchService(FakeUserModelRepository(build_user_model()))

    payload = search_memory(service, query="travel")

    assert payload == {
        "success": True,
        "results": [],
        "hint": SEARCH_MEMORY_NO_RESULTS_HINT,
    }


def test_search_memory_applies_top_k_limit() -> None:
    user_model = UserModel(
        facts=[
            FactItem(id="fact_001", category="identity", text="Night owl"),
            FactItem(id="fact_002", category="note", text="Night coding"),
        ],
        preferences=[TextItem(id="preference_001", text="Night walks")],
    )
    service = MemorySearchService(FakeUserModelRepository(user_model), top_k=2)

    payload = search_memory(service, query="night")

    assert payload["success"] is True
    assert len(payload["results"]) == 2


def test_ingest_turn_normalizes_messages_and_returns_result() -> None:
    service = IngestService(
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


def test_get_user_profile_returns_structured_internal_error_on_runtime_failure() -> None:
    service = RecallService(FailingUserModelRepository())

    payload = get_user_profile(service)

    assert payload == {
        "success": False,
        "error_type": "internal_error",
        "message": "User model storage unavailable",
        "hint": USER_PROFILE_UNAVAILABLE_HINT,
    }


def test_search_memory_returns_structured_internal_error_on_runtime_failure() -> None:
    service = MemorySearchService(FailingUserModelRepository())

    payload = search_memory(service, query="night")

    assert payload == {
        "success": False,
        "error_type": "internal_error",
        "message": "User model storage unavailable",
        "hint": SEARCH_MEMORY_FAILED_HINT,
    }


def test_ingest_turn_returns_structured_internal_error_on_runtime_failure() -> None:
    service = IngestService(
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
