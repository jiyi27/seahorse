from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seahorse import logger
from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.infrastructure.config import (
    AppPaths,
    load_logger_settings_from_env,
    load_provider_settings_from_env,
)
from seahorse.infrastructure.episodes.noop_episode_pipeline import NoopEpisodePipeline
from seahorse.infrastructure.extractors.llm_user_model_extractor import (
    LLMUserModelExtractor,
)
from seahorse.infrastructure.providers.factory import build_llm_provider
from seahorse.infrastructure.repositories.core_rule_markdown import (
    MarkdownCoreRuleRepository,
)
from seahorse.infrastructure.repositories.user_model_markdown import (
    MarkdownUserModelRepository,
)


@dataclass(frozen=True)
class AppContainer:
    recall_service: RecallService
    ingest_service: IngestService


def build_app_container(project_root: Path) -> AppContainer:
    paths = AppPaths.from_project_root(project_root)
    logger_settings = load_logger_settings_from_env()
    log_dir = Path(logger_settings.log_dir)
    if not log_dir.is_absolute():
        log_dir = project_root / log_dir
    logger.configure(log_dir=log_dir, level=logger_settings.log_level)
    logger.info("seahorse.startup", {"project_root": str(project_root)})
    provider_settings = load_provider_settings_from_env()

    core_rule_repository = MarkdownCoreRuleRepository(paths.storage.core_rule_path)
    user_model_repository = MarkdownUserModelRepository(paths.storage.user_model_path)
    provider = build_llm_provider(provider_settings)
    extractor = LLMUserModelExtractor(
        provider=provider,
        prompt_path=paths.prompt_dir / "user_model_extraction.md",
    )

    recall_service = RecallService(
        core_rule_repository=core_rule_repository,
        user_model_repository=user_model_repository,
    )
    ingest_service = IngestService(
        core_rule_repository=core_rule_repository,
        user_model_repository=user_model_repository,
        extractor=extractor,
        merger=UserModelMerger(),
        episode_pipeline=NoopEpisodePipeline(),
    )

    return AppContainer(
        recall_service=recall_service,
        ingest_service=ingest_service,
    )
