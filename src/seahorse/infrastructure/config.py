from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from seahorse.domain.models import ProviderSettings

_DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_PROVIDER_TIMEOUT_SECONDS = 60.0
_DEFAULT_APP_NAME = "Seahorse"


@dataclass(frozen=True)
class StoragePaths:
    data_dir: Path
    core_rule_path: Path
    user_model_path: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "StoragePaths":
        data_dir = project_root / "data"
        return cls(
            data_dir=data_dir,
            core_rule_path=data_dir / "core_rule.md",
            user_model_path=data_dir / "user_model.md",
        )


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    storage: StoragePaths
    prompt_dir: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "AppPaths":
        return cls(
            project_root=project_root,
            storage=StoragePaths.from_project_root(project_root),
            prompt_dir=project_root / "src" / "seahorse" / "prompts",
        )


@dataclass(frozen=True)
class LoggerSettings:
    log_dir: str = "logs"
    log_level: str = "info"


def load_logger_settings_from_env() -> LoggerSettings:
    return LoggerSettings(
        log_dir=os.environ.get("SEAHORSE_LOG_DIR", "logs"),
        log_level=os.environ.get("SEAHORSE_LOG_LEVEL", "info"),
    )


def load_provider_settings_from_env() -> ProviderSettings:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("SEAHORSE_MODEL")
    if not api_key:
        raise RuntimeError("Missing required environment variable: OPENROUTER_API_KEY")
    if not model:
        raise RuntimeError("Missing required environment variable: SEAHORSE_MODEL")

    return ProviderSettings(
        provider="openrouter",
        model=model,
        api_key=api_key,
        base_url=_DEFAULT_OPENROUTER_BASE_URL,
        timeout_seconds=_DEFAULT_PROVIDER_TIMEOUT_SECONDS,
        app_name=_DEFAULT_APP_NAME,
        referer=None,
    )
