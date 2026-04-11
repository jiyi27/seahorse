from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

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
    DEFAULT_MEMORY_SEARCH_TOP_K,
    SecretSettings,
    USER_MODEL_EXTRACTION_PROMPT_FILE_NAME,
    USER_MODEL_FILE_NAME,
    load_app_config_from_yaml,
    load_secrets_from_env,
)
from seahorse.infrastructure.pipelines.noop_conversation_vector_pipeline import (
    NoopConversationVectorPipeline,
)
from seahorse.infrastructure.providers.config import build_provider_settings
from seahorse.infrastructure.providers.factory import build_llm_provider
from seahorse.infrastructure.providers.openrouter import OpenRouterProvider


def write_minimal_runtime_files(
    project_root: Path,
    *,
    config_text: str = "",
) -> None:
    prompt_dir = project_root / "src" / "seahorse" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME).write_text(
        "Return JSON.",
        encoding="utf-8",
    )

    (project_root / DEFAULT_CONFIG_FILE_NAME).write_text(config_text, encoding="utf-8")


def test_load_secrets_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    app_config = AppConfig.model_validate({"storage": {"data_dir": "data"}})

    settings = load_secrets_from_env(app_config)

    assert settings.openrouter_api_key == "test-key"
    assert settings.embedding_api_key is None


def test_load_secrets_from_env_loads_embedding_api_key_when_vector_memory_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("TEST_EMBEDDING_KEY", "embed-key")

    settings = load_secrets_from_env(
        AppConfig.model_validate(
            {
                "storage": {"data_dir": "data"},
                "vector_memory": {"enabled": True},
                "embedding": {
                    "model": "text-embedding-3-small",
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "TEST_EMBEDDING_KEY",
                },
                "qdrant": {"url": "http://localhost:6333"},
            }
        )
    )

    assert settings.embedding_api_key == "embed-key"


def test_load_app_config_from_yaml_requires_explicit_storage_block(tmp_path: Path) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_FILE_NAME
    config_path.write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="storage"):
        load_app_config_from_yaml(config_path)


def test_load_app_config_from_yaml_applies_defaults_with_explicit_storage(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_FILE_NAME
    config_path.write_text("storage:\n  data_dir: data\n", encoding="utf-8")

    config = load_app_config_from_yaml(config_path)

    assert isinstance(config, AppConfig)
    assert config.provider.name == OPENROUTER_PROVIDER
    assert config.provider.model is None
    assert config.provider.timeout_seconds == 60.0
    assert config.logger.log_dir == DEFAULT_LOG_DIR
    assert config.logger.log_level == DEFAULT_LOG_LEVEL
    assert config.mcp.enabled_tools == list(DEFAULT_ENABLED_MCP_TOOLS)
    assert config.memory_search.top_k == DEFAULT_MEMORY_SEARCH_TOP_K
    assert config.storage.data_dir == "data"


def test_checked_in_config_yaml_is_valid() -> None:
    project_root = Path(__file__).resolve().parents[1]

    config = load_app_config_from_yaml(project_root / "config.yaml")

    assert isinstance(config, AppConfig)


def test_checked_in_config_example_is_valid() -> None:
    project_root = Path(__file__).resolve().parents[1]

    config = load_app_config_from_yaml(project_root / "config.yaml.example")

    assert isinstance(config, AppConfig)


def test_load_app_config_from_yaml_rejects_unsupported_mcp_tool(tmp_path: Path) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_FILE_NAME
    config_path.write_text(
        (
            "mcp:\n"
            "  enabled_tools:\n"
            "    - unknown_tool\n"
            "storage:\n"
            "  data_dir: data\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="unsupported tool"):
        load_app_config_from_yaml(config_path)


def test_load_app_config_from_yaml_rejects_invalid_memory_search_top_k(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_FILE_NAME
    config_path.write_text(
        (
            "memory_search:\n"
            "  top_k: 0\n"
            "storage:\n"
            "  data_dir: data\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="memory_search.top_k"):
        load_app_config_from_yaml(config_path)


def test_app_config_requires_qdrant_when_vector_memory_enabled() -> None:
    with pytest.raises(ValidationError, match="qdrant.url"):
        AppConfig.model_validate(
            {
                "storage": {"data_dir": "data"},
                "vector_memory": {"enabled": True},
                "embedding": {
                    "model": "text-embedding-3-small",
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                },
            }
        )


def test_app_paths_resolve_expected_locations(tmp_path: Path) -> None:
    config = AppConfig.model_validate(
        {
            "storage": {
                "data_dir": "var/memory",
            },
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
                },
            }
        ).provider,
        load_secrets_from_env(
            AppConfig.model_validate({"storage": {"data_dir": "data"}})
        ),
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
        ),
    )

    container = build_app_container(tmp_path)

    assert container.recall_service is not None
    assert container.memory_search_service is not None
    assert container.session_ingest_service is not None
    assert container.enabled_mcp_tools == frozenset(DEFAULT_ENABLED_MCP_TOOLS)
    assert isinstance(
        container.session_ingest_service._conversation_vector_pipeline,
        NoopConversationVectorPipeline,
    )


def test_build_app_container_fails_fast_when_provider_model_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    write_minimal_runtime_files(
        tmp_path,
        config_text=(
            "storage:\n"
            "  data_dir: data\n"
        ),
    )

    with pytest.raises(RuntimeError, match="provider.model"):
        build_app_container(tmp_path)


def test_build_app_container_fails_fast_when_vector_memory_enabled_without_qdrant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "embed-key")
    write_minimal_runtime_files(
        tmp_path,
        config_text=(
            "provider:\n"
            "  model: openai/gpt-4.1-mini\n"
            "storage:\n"
            "  data_dir: data\n"
            "vector_memory:\n"
            "  enabled: true\n"
            "embedding:\n"
            "  model: text-embedding-3-small\n"
            "  base_url: https://api.openai.com/v1\n"
            "  api_key_env: OPENAI_API_KEY\n"
        ),
    )

    with pytest.raises(RuntimeError, match="qdrant.url"):
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
