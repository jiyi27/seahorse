from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from seahorse.constants import OPENROUTER_BASE_URL
from seahorse.domain.models import (
    ConversationInput,
    FactItem,
    Message,
    ProviderSettings,
    UserProfile,
)
from seahorse.infrastructure.config import USER_PROFILE_EXTRACTION_PROMPT_FILE_NAME
from seahorse.infrastructure.extractors.llm_user_profile_extractor import (
    LLMUserProfileExtractor,
)
from seahorse.infrastructure.providers.base import LLMProvider
from seahorse.infrastructure.providers.openrouter import OpenRouterProvider


class FakeProvider(LLMProvider):
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0
        self.last_system_prompt = ""
        self.last_user_prompt = ""

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response


def test_llm_user_profile_extractor_builds_patch_from_provider_output(tmp_path: Path) -> None:
    prompt_path = tmp_path / USER_PROFILE_EXTRACTION_PROMPT_FILE_NAME
    prompt_path.write_text("Extract stable user information.", encoding="utf-8")
    provider = FakeProvider(
        (
            '{"summary":"Prefers concise answers.",'
            '"fact_ids_to_remove":[],'
            '"preferences_to_add":["Concise answers"],'
            '"preference_ids_to_remove":[],'
            '"facts_to_add":[{"category":"identity","text":"Uses Python"}],'
            '"constraints_to_add":[],"constraint_ids_to_remove":[]}'
        )
    )
    extractor = LLMUserProfileExtractor(provider=provider, prompt_path=prompt_path)

    patch = extractor.extract(
        conversation=ConversationInput(
            source="mcp",
            messages=[Message(role="user", text="Please keep answers concise. I use Python.")],
        ),
        current_user_profile=UserProfile(
            summary="Already knows some basics.",
            facts=[FactItem(id="fact_001", category="identity", text="Uses Rust")],
        ),
    )

    assert patch.summary == "Prefers concise answers."
    assert patch.preferences_to_add == ["Concise answers"]
    assert len(patch.facts_to_add) == 1
    assert patch.facts_to_add[0].category == "identity"
    assert patch.facts_to_add[0].text == "Uses Python"
    assert patch.fact_ids_to_remove == []
    assert provider.calls == 1
    assert "Current user profile:" in provider.last_user_prompt
    assert '"category": "identity"' in provider.last_user_prompt
    assert "I use Python." in provider.last_user_prompt


def test_llm_user_profile_extractor_prompt_uses_user_messages_only(tmp_path: Path) -> None:
    prompt_path = tmp_path / USER_PROFILE_EXTRACTION_PROMPT_FILE_NAME
    prompt_path.write_text("Extract stable user information.", encoding="utf-8")
    provider = FakeProvider(
        (
            '{"summary":"","fact_ids_to_remove":[],"preferences_to_add":[],'
            '"preference_ids_to_remove":[],"facts_to_add":[],'
            '"constraints_to_add":[],"constraint_ids_to_remove":[]}'
        )
    )
    extractor = LLMUserProfileExtractor(provider=provider, prompt_path=prompt_path)

    extractor.extract(
        conversation=ConversationInput(
            source="mcp",
            messages=[
                Message(role="assistant", text="What should I remember?"),
                Message(role="user", text="Remember that I prefer concise answers."),
                Message(role="tool", text="tool output"),
            ],
        ),
        current_user_profile=None,
    )

    assert "Remember that I prefer concise answers." in provider.last_user_prompt
    assert "What should I remember?" not in provider.last_user_prompt
    assert "tool output" not in provider.last_user_prompt


def test_llm_user_profile_extractor_rejects_invalid_json(tmp_path: Path) -> None:
    prompt_path = tmp_path / USER_PROFILE_EXTRACTION_PROMPT_FILE_NAME
    prompt_path.write_text("Extract stable user information.", encoding="utf-8")
    provider = FakeProvider("not-json")
    extractor = LLMUserProfileExtractor(provider=provider, prompt_path=prompt_path)

    with pytest.raises(RuntimeError, match="invalid JSON"):
        extractor.extract(
            conversation=ConversationInput(source="http", content="User prefers brief answers."),
            current_user_profile=None,
        )


def test_openrouter_provider_formats_request_and_reads_response() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("Authorization")
        captured["title"] = request.headers.get("X-Title")
        captured["payload"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "  {\"summary\":\"Stable user preference\"}  "
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = OpenRouterProvider(
        settings=ProviderSettings(
            model="openai/gpt-4.1-mini",
            api_key="test-key",
            app_name="Seahorse Tests",
            referer="https://example.com",
        ),
        http_client=client,
    )

    response = provider.complete(system_prompt="system", user_prompt="user")

    assert response == '{"summary":"Stable user preference"}'
    assert captured["url"] == f"{OPENROUTER_BASE_URL}/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["title"] == "Seahorse Tests"
    assert '"model":"openai/gpt-4.1-mini"' in str(captured["payload"])
