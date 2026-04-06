from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from seahorse.constants import OPENROUTER_PROVIDER
from seahorse.tools.tool_names import ALL_TOOL_NAMES

DEFAULT_CONFIG_FILE_NAME = "config.yaml"
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_LEVEL = "info"
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 60.0
SUPPORTED_LOG_LEVELS = frozenset({"debug", "info", "warning", "error"})
USER_MODEL_FILE_NAME = "user_model.json"
USER_MODEL_EXTRACTION_PROMPT_FILE_NAME = "user_model_extraction.md"
DEFAULT_ENABLED_MCP_TOOLS = tuple(sorted(ALL_TOOL_NAMES))


def _raise_config_error(message: str, *, cause: Exception | None = None) -> None:
    if cause is None:
        raise RuntimeError(message)
    raise RuntimeError(message) from cause


def _resolve_project_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return project_root / path


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = OPENROUTER_PROVIDER
    model: str | None = None
    timeout_seconds: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS

    @field_validator("name")
    @classmethod
    def validate_provider_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("provider.name must not be empty")
        return normalized

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("provider.model must not be empty")
        return normalized

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("provider.timeout_seconds must be greater than 0")
        return value


class LoggerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_dir: str = DEFAULT_LOG_DIR
    log_level: str = DEFAULT_LOG_LEVEL

    @field_validator("log_dir")
    @classmethod
    def validate_log_dir(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("logger.log_dir must not be empty")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_LOG_LEVELS:
            valid = ", ".join(sorted(SUPPORTED_LOG_LEVELS))
            raise ValueError(
                f"logger.log_level must be one of: {valid}"
            )
        return normalized


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_dir: str
    persona_dir: str
    persona_name: str

    @field_validator("data_dir", "persona_dir", "persona_name")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("storage values must not be empty")
        return normalized

    @field_validator("persona_name")
    @classmethod
    def validate_persona_name(cls, value: str) -> str:
        if Path(value).name != value or value.endswith(".md"):
            raise ValueError(
                "storage.persona_name must be a bare persona name without path segments"
            )
        return value


class MCPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_tools: list[str] = list(DEFAULT_ENABLED_MCP_TOOLS)

    @field_validator("enabled_tools")
    @classmethod
    def validate_enabled_tools(cls, value: list[str]) -> list[str]:
        normalized_tools: list[str] = []
        seen_tools: set[str] = set()
        for raw_tool_name in value:
            tool_name = raw_tool_name.strip()
            if not tool_name:
                raise ValueError("mcp.enabled_tools must not contain empty values")
            if tool_name not in ALL_TOOL_NAMES:
                valid = ", ".join(sorted(ALL_TOOL_NAMES))
                raise ValueError(
                    f"mcp.enabled_tools contains unsupported tool '{tool_name}'. "
                    f"Supported tools: {valid}"
                )
            if tool_name not in seen_tools:
                normalized_tools.append(tool_name)
                seen_tools.add(tool_name)
        return normalized_tools


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderConfig = ProviderConfig()
    logger: LoggerConfig = LoggerConfig()
    mcp: MCPConfig = MCPConfig()
    storage: StorageConfig


@dataclass(frozen=True)
class SecretSettings:
    openrouter_api_key: str


@dataclass(frozen=True)
class StoragePaths:
    data_dir: Path
    user_model_path: Path

    @classmethod
    def from_config(cls, project_root: Path, storage_config: StorageConfig) -> "StoragePaths":
        data_dir = _resolve_project_path(project_root, storage_config.data_dir)
        return cls(
            data_dir=data_dir,
            user_model_path=data_dir / USER_MODEL_FILE_NAME,
        )


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    storage: StoragePaths
    prompt_dir: Path
    user_model_extraction_prompt_path: Path
    persona_dir: Path
    persona_path: Path

    @classmethod
    def from_config(cls, project_root: Path, app_config: AppConfig) -> "AppPaths":
        prompt_dir = project_root / "src" / "seahorse" / "prompts"
        storage_paths = StoragePaths.from_config(project_root, app_config.storage)
        persona_dir = _resolve_project_path(project_root, app_config.storage.persona_dir)
        return cls(
            project_root=project_root,
            storage=storage_paths,
            prompt_dir=prompt_dir,
            user_model_extraction_prompt_path=(
                prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME
            ),
            persona_dir=persona_dir,
            persona_path=persona_dir / f"{app_config.storage.persona_name}.md",
        )


def load_secrets_from_env() -> SecretSettings:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        _raise_config_error(
            "Missing required environment variable: OPENROUTER_API_KEY"
        )
    return SecretSettings(openrouter_api_key=api_key)


def load_app_config_from_yaml(path: Path) -> AppConfig:
    if not path.exists():
        _raise_config_error(f"Missing configuration file: {path}")

    try:
        raw_content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        _raise_config_error(f"Invalid YAML in configuration file: {path}", cause=exc)
    except OSError as exc:
        _raise_config_error(f"Failed to read configuration file: {path}", cause=exc)

    if raw_content is None:
        payload: dict[str, Any] = {}
    elif isinstance(raw_content, dict):
        payload = raw_content
    else:
        _raise_config_error(f"Configuration file must contain a YAML mapping: {path}")

    try:
        return AppConfig.model_validate(payload)
    except ValidationError as exc:
        _raise_config_error(
            f"Invalid application configuration in {path}: {exc}",
            cause=exc,
        )


def validate_app_paths(paths: AppPaths) -> None:
    if not paths.user_model_extraction_prompt_path.exists():
        _raise_config_error(
            "Missing required prompt file: "
            f"{paths.user_model_extraction_prompt_path}"
        )
    if not paths.persona_path.exists():
        _raise_config_error(
            "Missing configured persona file: "
            f"{paths.persona_path}"
        )
