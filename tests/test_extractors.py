from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from seahorse.domain.models import ConversationInput, CoreRule, Message, ProviderSettings, UserModel
from seahorse.infrastructure.extractors.llm_user_model_extractor import (
    LLMUserModelExtractor,
)
from seahorse.infrastructure.providers.openrouter import OpenRouterProvider


class FakeProvider:
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


def test_llm_user_model_extractor_builds_patch_from_provider_output(tmp_path: Path) -> None:
    prompt_path = tmp_path / "user_model_extraction.md"
    prompt_path.write_text("Extract stable user information.", encoding="utf-8")
    provider = FakeProvider(
        (
            '{"summary":"Prefers concise answers.",'
            '"facts_to_remove":[],'
            '"preferences_to_add":["Concise answers"],'
            '"preferences_to_remove":[],'
            '"facts_to_add":["Uses Python"],'
            '"constraints_to_add":[],"constraints_to_remove":[]}'
        )
    )
    extractor = LLMUserModelExtractor(provider=provider, prompt_path=prompt_path)

    patch = extractor.extract(
        conversation=ConversationInput(
            source="mcp",
            messages=[Message(role="user", text="Please keep answers concise. I use Python.")],
        ),
        current_user_model=UserModel(content="## Summary\n\nNo summary yet.\n", version=2),
        core_rule=CoreRule(content="Be precise."),
    )

    assert patch.summary == "Prefers concise answers."
    assert patch.preferences_to_add == ["Concise answers"]
    assert patch.facts_to_add == ["Uses Python"]
    assert patch.facts_to_remove == []
    assert provider.calls == 1
    assert "Be precise." in provider.last_user_prompt
    assert "I use Python." in provider.last_user_prompt


def test_llm_user_model_extractor_rejects_invalid_json(tmp_path: Path) -> None:
    prompt_path = tmp_path / "user_model_extraction.md"
    prompt_path.write_text("Extract stable user information.", encoding="utf-8")
    provider = FakeProvider("not-json")
    extractor = LLMUserModelExtractor(provider=provider, prompt_path=prompt_path)

    with pytest.raises(RuntimeError, match="invalid JSON"):
        extractor.extract(
            conversation=ConversationInput(source="http", content="User prefers brief answers."),
            current_user_model=None,
            core_rule=CoreRule(content="Be precise."),
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
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["title"] == "Seahorse Tests"
    assert '"model":"openai/gpt-4.1-mini"' in str(captured["payload"])
