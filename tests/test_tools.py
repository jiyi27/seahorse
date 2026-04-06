from __future__ import annotations

import pytest

from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.application.user_model_renderer import UserModelRenderer
from seahorse.domain.models import Persona, TextItem, UserModel, UserModelPatch
from seahorse.tools.contracts import INGEST_RETRY_HINT, RECALL_CONTEXT_UNAVAILABLE_HINT
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.recall_context import recall_context


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
            summary="Prefers direct answers.",
            preferences_to_add=["Direct answers"],
        )


class FakeEpisodePipeline:
    def process(self, conversation) -> None:
        return None


class FailingPersonaRepository:
    def load(self) -> Persona:
        raise RuntimeError("Persona storage unavailable")


def test_recall_context_returns_string_payload() -> None:
    service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(
            UserModel(
                summary="Prefers direct answers.",
                preferences=[TextItem(id="preference_001", text="Direct answers")],
            )
        ),
    )

    payload = recall_context(service, UserModelRenderer())

    assert payload["success"] is True
    assert payload["persona"] == "Be precise."
    assert "Prefers direct answers." in payload["user_model"]


def test_recall_context_returns_none_when_user_model_missing() -> None:
    service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(),
    )

    payload = recall_context(service, UserModelRenderer())

    assert payload == {
        "success": True,
        "persona": "Be precise.",
        "user_model": None,
    }


def test_recall_context_returns_none_when_user_model_is_empty() -> None:
    service = RecallService(
        persona_repository=FakePersonaRepository(Persona(content="Be precise.")),
        user_model_repository=FakeUserModelRepository(UserModel()),
    )

    payload = recall_context(service, UserModelRenderer())

    assert payload == {
        "success": True,
        "persona": "Be precise.",
        "user_model": None,
    }


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


def test_recall_context_returns_structured_internal_error_on_runtime_failure() -> None:
    service = RecallService(
        persona_repository=FailingPersonaRepository(),
        user_model_repository=FakeUserModelRepository(),
    )

    payload = recall_context(service, UserModelRenderer())

    assert payload == {
        "success": False,
        "error_type": "internal_error",
        "message": "Persona storage unavailable",
        "hint": RECALL_CONTEXT_UNAVAILABLE_HINT,
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
