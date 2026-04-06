from __future__ import annotations

from pathlib import Path

from seahorse.bootstrap import build_app_container
from seahorse.domain.models import ProviderSettings
from seahorse.infrastructure.config import (
    AppPaths,
    load_logger_settings_from_env,
    load_provider_settings_from_env,
)
from seahorse.infrastructure.providers.factory import build_llm_provider
from seahorse.infrastructure.providers.openrouter import OpenRouterProvider


def test_load_provider_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("SEAHORSE_MODEL", "openai/gpt-4.1-mini")

    settings = load_provider_settings_from_env()

    assert settings.api_key == "test-key"
    assert settings.model == "openai/gpt-4.1-mini"
    assert settings.timeout_seconds == 60.0
    assert settings.base_url == "https://openrouter.ai/api/v1"
    assert settings.app_name == "Seahorse"
    assert settings.referer is None


def test_app_paths_resolve_expected_locations(tmp_path: Path) -> None:
    paths = AppPaths.from_project_root(tmp_path)

    assert paths.storage.core_rule_path == tmp_path / "data" / "core_rule.md"
    assert paths.storage.user_model_path == tmp_path / "data" / "user_model.md"
    assert paths.prompt_dir == tmp_path / "src" / "seahorse" / "prompts"


def test_load_logger_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("SEAHORSE_LOG_DIR", "var/logs/seahorse")
    monkeypatch.setenv("SEAHORSE_LOG_LEVEL", "debug")

    settings = load_logger_settings_from_env()

    assert settings.log_dir == "var/logs/seahorse"
    assert settings.log_level == "debug"


def test_build_app_container_wires_services(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("SEAHORSE_MODEL", "openai/gpt-4.1-mini")

    prompt_dir = tmp_path / "src" / "seahorse" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "user_model_extraction.md").write_text(
        "Return JSON.",
        encoding="utf-8",
    )

    container = build_app_container(tmp_path)

    assert container.recall_service is not None
    assert container.ingest_service is not None


def test_build_llm_provider_uses_configured_provider() -> None:
    provider = build_llm_provider(
        ProviderSettings(
            provider="openrouter",
            model="openai/gpt-4.1-mini",
            api_key="test-key",
        )
    )

    assert isinstance(provider, OpenRouterProvider)
