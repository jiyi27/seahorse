from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seahorse import logger
from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.recall_service import RecallService
from seahorse.application.session_ingest_service import SessionIngestService
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.application.user_profile_ingest_service import UserProfileIngestService
from seahorse.application.user_model_renderer import UserModelRenderer
from seahorse.infrastructure.config import (
    AppPaths,
    DEFAULT_CONFIG_FILE_NAME,
    load_app_config_from_yaml,
    load_secrets_from_env,
    validate_app_paths,
)
from seahorse.infrastructure.episodes.noop_episode_pipeline import NoopEpisodePipeline
from seahorse.infrastructure.extractors.llm_user_model_extractor import (
    LLMUserModelExtractor,
)
from seahorse.infrastructure.providers.config import build_provider_settings
from seahorse.infrastructure.providers.factory import build_llm_provider
from seahorse.infrastructure.repositories.user_model_json import (
    JSONUserModelRepository,
)


@dataclass(frozen=True)
class AppContainer:
    recall_service: RecallService
    memory_search_service: MemorySearchService
    session_ingest_service: SessionIngestService
    user_model_renderer: UserModelRenderer
    enabled_mcp_tools: frozenset[str]


def build_app_container(
    project_root: Path, config_path: Path | None = None
) -> AppContainer:
    resolved_config_path = config_path or project_root / DEFAULT_CONFIG_FILE_NAME
    app_config = load_app_config_from_yaml(resolved_config_path)
    secrets = load_secrets_from_env()
    paths = AppPaths.from_config(project_root, app_config)
    validate_app_paths(paths)

    log_dir = Path(app_config.logger.log_dir)
    if not log_dir.is_absolute():
        log_dir = project_root / log_dir
    logger.configure(log_dir=log_dir, level=app_config.logger.log_level)
    logger.info("seahorse.startup", {"project_root": str(project_root)})
    provider_settings = build_provider_settings(app_config.provider, secrets)

    user_model_repository = JSONUserModelRepository(paths.storage.user_model_path)
    provider = build_llm_provider(provider_settings)
    extractor = LLMUserModelExtractor(
        provider=provider,
        prompt_path=paths.user_model_extraction_prompt_path,
    )
    user_model_renderer = UserModelRenderer()

    recall_service = RecallService(user_model_repository=user_model_repository)
    memory_search_service = MemorySearchService(
        user_model_repository=user_model_repository,
        top_k=app_config.memory_search.top_k,
    )
    user_profile_ingest_service = UserProfileIngestService(
        user_model_repository=user_model_repository,
        extractor=extractor,
        merger=UserModelMerger(),
        episode_pipeline=NoopEpisodePipeline(),
    )
    session_ingest_service = SessionIngestService(
        user_profile_ingest_service=user_profile_ingest_service
    )

    return AppContainer(
        recall_service=recall_service,
        memory_search_service=memory_search_service,
        session_ingest_service=session_ingest_service,
        user_model_renderer=user_model_renderer,
        enabled_mcp_tools=frozenset(app_config.mcp.enabled_tools),
    )
