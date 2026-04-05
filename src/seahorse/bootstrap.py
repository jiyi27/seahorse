from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seahorse.application.ingest_service import IngestService
from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.infrastructure.config import AppPaths, load_provider_settings_from_env
from seahorse.infrastructure.episodes.noop_episode_pipeline import NoopEpisodePipeline
from seahorse.infrastructure.extractors.llm_user_model_extractor import (
    LLMUserModelExtractor,
)
from seahorse.infrastructure.providers.openrouter import OpenRouterProvider
from seahorse.infrastructure.repositories.core_rule_markdown import (
    MarkdownCoreRuleRepository,
)
from seahorse.infrastructure.repositories.user_model_markdown import (
    MarkdownUserModelRepository,
)


@dataclass(frozen=True)
class AppContainer:
    paths: AppPaths
    recall_service: RecallService
    ingest_service: IngestService


def build_app_container(project_root: Path) -> AppContainer:
    paths = AppPaths.from_project_root(project_root)
    provider_settings = load_provider_settings_from_env()

    core_rule_repository = MarkdownCoreRuleRepository(paths.storage.core_rule_path)
    user_model_repository = MarkdownUserModelRepository(paths.storage.user_model_path)
    provider = OpenRouterProvider(provider_settings)
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
        paths=paths,
        recall_service=recall_service,
        ingest_service=ingest_service,
    )
