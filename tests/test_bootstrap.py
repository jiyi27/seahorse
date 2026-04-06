from __future__ import annotations

from pathlib import Path

import pytest

from seahorse.bootstrap import build_app_container
from seahorse.constants import APP_NAME, OPENROUTER_BASE_URL, OPENROUTER_PROVIDER
from seahorse.domain.models import ProviderSettings
from seahorse.infrastructure.config import (
    AppConfig,
    AppPaths,
    DEFAULT_CONFIG_FILE_NAME,
    DEFAULT_ENABLED_MCP_TOOLS,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_LEVEL,
    SecretSettings,
    USER_MODEL_EXTRACTION_PROMPT_FILE_NAME,
    USER_MODEL_FILE_NAME,
    load_app_config_from_yaml,
    load_secrets_from_env,
    validate_app_paths,
)
from seahorse.infrastructure.providers.config import build_provider_settings
from seahorse.infrastructure.providers.factory import build_llm_provider
from seahorse.infrastructure.providers.openrouter import OpenRouterProvider


def write_minimal_runtime_files(
    project_root: Path,
    *,
    config_text: str = "",
    persona_name: str = "default",
) -> None:
    prompt_dir = project_root / "src" / "seahorse" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME).write_text(
        "Return JSON.",
        encoding="utf-8",
    )

    persona_dir = project_root / "personas"
    persona_dir.mkdir(parents=True)
    (persona_dir / f"{persona_name}.md").write_text(
        "# Core Rule\n\nBe precise.\n",
        encoding="utf-8",
    )

    (project_root / DEFAULT_CONFIG_FILE_NAME).write_text(config_text, encoding="utf-8")


def test_load_secrets_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    settings = load_secrets_from_env()

    assert settings.openrouter_api_key == "test-key"


def test_load_app_config_from_yaml_requires_explicit_storage_block(tmp_path: Path) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_FILE_NAME
    config_path.write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="storage"):
        load_app_config_from_yaml(config_path)


def test_load_app_config_from_yaml_applies_defaults_with_explicit_storage(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_FILE_NAME
    config_path.write_text(
        "storage:\n  data_dir: data\n  persona_dir: personas\n  persona_name: default\n",
        encoding="utf-8",
    )

    config = load_app_config_from_yaml(config_path)

    assert isinstance(config, AppConfig)
    assert config.provider.name == OPENROUTER_PROVIDER
    assert config.provider.model is None
    assert config.provider.timeout_seconds == 60.0
    assert config.logger.log_dir == DEFAULT_LOG_DIR
    assert config.logger.log_level == DEFAULT_LOG_LEVEL
    assert config.mcp.enabled_tools == list(DEFAULT_ENABLED_MCP_TOOLS)
    assert config.storage.data_dir == "data"
    assert config.storage.persona_dir == "personas"
    assert config.storage.persona_name == "default"


def test_load_app_config_from_yaml_rejects_unsupported_mcp_tool(tmp_path: Path) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_FILE_NAME
    config_path.write_text(
        (
            "mcp:\n"
            "  enabled_tools:\n"
            "    - unknown_tool\n"
            "storage:\n"
            "  data_dir: data\n"
            "  persona_dir: personas\n"
            "  persona_name: default\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="unsupported tool"):
        load_app_config_from_yaml(config_path)


def test_app_paths_resolve_expected_locations(tmp_path: Path) -> None:
    config = AppConfig.model_validate(
        {
            "storage": {
                "data_dir": "var/memory",
                "persona_dir": "personas",
                "persona_name": "analyst",
            }
        }
    )

    paths = AppPaths.from_config(tmp_path, config)

    assert paths.storage.data_dir == tmp_path / "var" / "memory"
    assert paths.storage.user_model_path == tmp_path / "var" / "memory" / USER_MODEL_FILE_NAME
    assert paths.prompt_dir == tmp_path / "src" / "seahorse" / "prompts"
    assert (
        paths.user_model_extraction_prompt_path
        == paths.prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME
    )
    assert paths.persona_dir == tmp_path / "personas"
    assert paths.persona_path == tmp_path / "personas" / "analyst.md"


def test_validate_app_paths_rejects_missing_persona_file(tmp_path: Path) -> None:
    config = AppConfig.model_validate(
        {
            "storage": {
                "data_dir": "data",
                "persona_dir": "personas",
                "persona_name": "default",
            }
        }
    )
    prompt_dir = tmp_path / "src" / "seahorse" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME).write_text(
        "Return JSON.",
        encoding="utf-8",
    )

    paths = AppPaths.from_config(tmp_path, config)

    with pytest.raises(RuntimeError, match="Missing configured persona file"):
        validate_app_paths(paths)


def test_build_provider_settings_uses_yaml_model_and_env_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    provider_settings = build_provider_settings(
        AppConfig.model_validate(
            {
                "provider": {"name": "openrouter", "model": "openai/gpt-4.1-mini"},
                "storage": {
                    "data_dir": "data",
                    "persona_dir": "personas",
                    "persona_name": "default",
                },
            }
        ).provider,
        load_secrets_from_env(),
    )

    assert provider_settings.api_key == "test-key"
    assert provider_settings.model == "openai/gpt-4.1-mini"
    assert provider_settings.timeout_seconds == 60.0
    assert provider_settings.base_url == OPENROUTER_BASE_URL
    assert provider_settings.app_name == APP_NAME
    assert provider_settings.referer is None


def test_build_provider_settings_requires_model_for_openrouter(
) -> None:
    with pytest.raises(RuntimeError, match="provider.model"):
        build_provider_settings(
            AppConfig.model_validate(
                {
                    "provider": {"name": "openrouter"},
                    "storage": {
                        "data_dir": "data",
                        "persona_dir": "personas",
                        "persona_name": "default",
                    },
                }
            ).provider,
            SecretSettings(openrouter_api_key="test-key"),
        )


def test_build_app_container_wires_services(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    write_minimal_runtime_files(
        tmp_path,
        config_text=(
            "provider:\n"
            "  model: openai/gpt-4.1-mini\n"
            "storage:\n"
            "  data_dir: data\n"
            "  persona_dir: personas\n"
            "  persona_name: default\n"
        ),
    )

    container = build_app_container(tmp_path)

    assert container.recall_service is not None
    assert container.ingest_service is not None
    assert container.enabled_mcp_tools == frozenset(DEFAULT_ENABLED_MCP_TOOLS)


def test_build_app_container_fails_fast_when_provider_model_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    write_minimal_runtime_files(
        tmp_path,
        config_text=(
            "storage:\n"
            "  data_dir: data\n"
            "  persona_dir: personas\n"
            "  persona_name: default\n"
        ),
    )

    with pytest.raises(RuntimeError, match="provider.model"):
        build_app_container(tmp_path)


def test_build_llm_provider_uses_configured_provider() -> None:
    provider = build_llm_provider(
        ProviderSettings(
            provider=OPENROUTER_PROVIDER,
            model="openai/gpt-4.1-mini",
            api_key="test-key",
        )
    )

    assert isinstance(provider, OpenRouterProvider)
