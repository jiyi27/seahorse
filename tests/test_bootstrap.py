from __future__ import annotations

from pathlib import Path

from seahorse.bootstrap import build_app_container
from seahorse.constants import APP_NAME, OPENROUTER_BASE_URL, OPENROUTER_PROVIDER
from seahorse.domain.models import ProviderSettings
from seahorse.infrastructure.config import (
    AppPaths,
    CORE_RULE_FILE_NAME,
    USER_MODEL_EXTRACTION_PROMPT_FILE_NAME,
    USER_MODEL_FILE_NAME,
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
    assert settings.base_url == OPENROUTER_BASE_URL
    assert settings.app_name == APP_NAME
    assert settings.referer is None


def test_app_paths_resolve_expected_locations(tmp_path: Path) -> None:
    paths = AppPaths.from_project_root(tmp_path)

    assert paths.storage.core_rule_path == tmp_path / "data" / CORE_RULE_FILE_NAME
    assert paths.storage.user_model_path == tmp_path / "data" / USER_MODEL_FILE_NAME
    assert paths.prompt_dir == tmp_path / "src" / "seahorse" / "prompts"
    assert (
        paths.user_model_extraction_prompt_path
        == paths.prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME
    )


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
    (prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME).write_text(
        "Return JSON.",
        encoding="utf-8",
    )

    container = build_app_container(tmp_path)

    assert container.recall_service is not None
    assert container.ingest_service is not None


def test_build_llm_provider_uses_configured_provider() -> None:
    provider = build_llm_provider(
        ProviderSettings(
            provider=OPENROUTER_PROVIDER,
            model="openai/gpt-4.1-mini",
            api_key="test-key",
        )
    )

    assert isinstance(provider, OpenRouterProvider)
