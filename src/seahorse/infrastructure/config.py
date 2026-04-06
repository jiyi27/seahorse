from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from seahorse.constants import APP_NAME, OPENROUTER_BASE_URL, OPENROUTER_PROVIDER
from seahorse.domain.models import ProviderSettings

_DEFAULT_PROVIDER_TIMEOUT_SECONDS = 60.0
CORE_RULE_FILE_NAME = "core_rule.md"
USER_MODEL_FILE_NAME = "user_model.md"
USER_MODEL_EXTRACTION_PROMPT_FILE_NAME = "user_model_extraction.md"


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
            core_rule_path=data_dir / CORE_RULE_FILE_NAME,
            user_model_path=data_dir / USER_MODEL_FILE_NAME,
        )


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    storage: StoragePaths
    prompt_dir: Path
    user_model_extraction_prompt_path: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "AppPaths":
        prompt_dir = project_root / "src" / "seahorse" / "prompts"
        return cls(
            project_root=project_root,
            storage=StoragePaths.from_project_root(project_root),
            prompt_dir=prompt_dir,
            user_model_extraction_prompt_path=(
                prompt_dir / USER_MODEL_EXTRACTION_PROMPT_FILE_NAME
            ),
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
        provider=OPENROUTER_PROVIDER,
        model=model,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        timeout_seconds=_DEFAULT_PROVIDER_TIMEOUT_SECONDS,
        app_name=APP_NAME,
        referer=None,
    )
