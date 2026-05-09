from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seahorse.infrastructure.embeddings.base import EmbeddingSettings
from seahorse.infrastructure.config import AppConfig, SecretSettings
from seahorse.infrastructure.embeddings.factory import build_embedding_model
from seahorse.infrastructure.pipelines.noop_conversation_vector_pipeline import (
    NoopConversationVectorPipeline,
)
from seahorse.infrastructure.pipelines.qdrant_conversation_vector_pipeline import (
    QdrantConversationVectorPipeline,
)
from seahorse.infrastructure.vectorstore.qdrant_store import (
    QdrantSettings,
    build_qdrant_vector_store,
)


@dataclass(frozen=True)
class VectorComponents:
    embedding_model: Any
    vector_store: Any


def build_vector_components(
    app_config: AppConfig,
    secrets: SecretSettings,
) -> VectorComponents | None:
    # Build the shared vector-layer dependencies for ingest and retrieval:
    # the embedding model and vector store.
    if not app_config.vector_memory.enabled:
        return None

    embedding_model = build_embedding_model(
        EmbeddingSettings(
            provider=app_config.vector_memory.embedding.provider,
            model=app_config.vector_memory.embedding.model or "",
            base_url=app_config.vector_memory.embedding.base_url or "",
            api_key=secrets.embedding_api_key,
            timeout_seconds=app_config.vector_memory.embedding.timeout_seconds,
        )
    )
    vector_store = build_qdrant_vector_store(
        QdrantSettings(
            url=app_config.vector_memory.store.url or "",
            collection_name=app_config.vector_memory.store.collection_name,
        )
    )
    return VectorComponents(
        embedding_model=embedding_model,
        vector_store=vector_store,
    )


def build_conversation_vector_pipeline(
    vector_components: VectorComponents | None,
):
    if vector_components is None:
        return NoopConversationVectorPipeline()

    return QdrantConversationVectorPipeline(
        embedding_model=vector_components.embedding_model,
        vector_store=vector_components.vector_store,
    )
