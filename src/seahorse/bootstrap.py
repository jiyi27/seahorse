from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seahorse import logger
from seahorse.application.health_service import HealthService
from seahorse.application.memory_search_service import MemorySearchService
from seahorse.application.session_ingest_service import SessionIngestService
from seahorse.application.user_profile_ingest_service import UserProfileIngestService
from seahorse.application.user_profile_merger import UserProfileMerger
from seahorse.domain.repositories import UserProfileRepository
from seahorse.retrieval.vector_health_service import VectorHealthService
from seahorse.retrieval.vector_search_service import VectorSearchService
from seahorse.infrastructure.config import (
    AppConfig,
    AppPaths,
    DEFAULT_CONFIG_FILE_NAME,
    SecretSettings,
    load_app_config_from_yaml,
    load_secrets_from_env,
    validate_app_paths,
)
from seahorse.infrastructure.extractors.llm_user_profile_extractor import (
    LLMUserProfileExtractor,
)
from seahorse.infrastructure.pipelines.factory import (
    build_conversation_vector_pipeline,
    build_vector_components,
    VectorComponents,
)
from seahorse.infrastructure.providers.config import build_provider_settings
from seahorse.infrastructure.providers.factory import build_llm_provider
from seahorse.infrastructure.repositories.user_profile_json import (
    JSONUserProfileRepository,
)


@dataclass(frozen=True)
class SeahorseRuntime:
    health_service: HealthService
    user_profile_repository: UserProfileRepository
    memory_search_service: MemorySearchService
    session_ingest_service: SessionIngestService
    enabled_mcp_tools: frozenset[str]


@dataclass(frozen=True)
class RuntimeBootstrapContext:
    app_config: AppConfig
    secrets: SecretSettings
    paths: AppPaths


def _configure_logging(project_root: Path, app_config: AppConfig) -> None:
    log_dir = Path(app_config.logger.log_dir)
    if not log_dir.is_absolute():
        log_dir = project_root / log_dir
    logger.configure(log_dir=log_dir, level=app_config.logger.log_level)


def _load_bootstrap_context(
    project_root: Path,
    config_path: Path | None = None,
) -> RuntimeBootstrapContext:
    resolved_config_path = config_path or project_root / DEFAULT_CONFIG_FILE_NAME
    app_config = load_app_config_from_yaml(resolved_config_path)
    secrets = load_secrets_from_env(app_config)
    paths = AppPaths.from_config(project_root, app_config)
    validate_app_paths(paths)
    _configure_logging(project_root, app_config)
    return RuntimeBootstrapContext(
        app_config=app_config,
        secrets=secrets,
        paths=paths,
    )


def _build_user_profile_ingest_service(
    paths: AppPaths,
    provider_settings: Any,
    user_profile_repository: JSONUserProfileRepository,
) -> UserProfileIngestService:
    provider = build_llm_provider(provider_settings)
    extractor = LLMUserProfileExtractor(
        provider=provider,
        prompt_path=paths.user_profile_extraction_prompt_path,
    )
    return UserProfileIngestService(
        user_profile_repository=user_profile_repository,
        extractor=extractor,
        merger=UserProfileMerger(),
    )


def _build_health_service(
    vector_components: VectorComponents | None,
) -> HealthService:
    vector_health_service = (
        None
        if vector_components is None
        else VectorHealthService(
            vector_components.embedding_model,
            vector_components.vector_store,
        )
    )
    return HealthService(vector_health_service=vector_health_service)


def _build_memory_search_service(
    app_config: AppConfig,
    vector_components: VectorComponents | None,
) -> MemorySearchService:
    vector_search_service = (
        None
        if vector_components is None
        else VectorSearchService(
            vector_components.embedding_model,
            vector_components.vector_store,
            max_chunks=app_config.vector_memory.retrieval.max_chunks,
            max_blocks=app_config.vector_memory.retrieval.max_blocks,
        )
    )
    return MemorySearchService(vector_search_service=vector_search_service)


def _build_session_ingest_service(
    user_profile_ingest_service: UserProfileIngestService,
    vector_components: VectorComponents | None,
) -> SessionIngestService:
    return SessionIngestService(
        user_profile_ingest_service=user_profile_ingest_service,
        conversation_vector_pipeline=build_conversation_vector_pipeline(vector_components),
    )


def _build_runtime(context: RuntimeBootstrapContext) -> SeahorseRuntime:
    provider_settings = build_provider_settings(
        context.app_config.provider,
        context.secrets,
    )
    user_profile_repository = JSONUserProfileRepository(
        context.paths.storage.user_profile_path
    )
    user_profile_ingest_service = _build_user_profile_ingest_service(
        context.paths,
        provider_settings,
        user_profile_repository,
    )
    # Shared vector-layer dependencies: the embedding model and vector store.
    vector_components = build_vector_components(
        context.app_config,
        context.secrets,
    )
    health_service = _build_health_service(vector_components)
    memory_search_service = _build_memory_search_service(
        context.app_config,
        vector_components,
    )
    session_ingest_service = _build_session_ingest_service(
        user_profile_ingest_service,
        vector_components,
    )

    return SeahorseRuntime(
        health_service=health_service,
        user_profile_repository=user_profile_repository,
        memory_search_service=memory_search_service,
        session_ingest_service=session_ingest_service,
        enabled_mcp_tools=frozenset(context.app_config.mcp.enabled_tools),
    )


def build_runtime(
    project_root: Path,
    config_path: Path | None = None,
) -> SeahorseRuntime:
    return _build_runtime(_load_bootstrap_context(project_root, config_path))
