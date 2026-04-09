from __future__ import annotations

import threading
from dataclasses import dataclass

from seahorse import logger
from seahorse.ingest.models import PreparedConversationChunk


@dataclass(frozen=True)
class QdrantSettings:
    url: str
    collection_name: str


class QdrantConversationVectorStore:
    def __init__(self, settings: QdrantSettings) -> None:
        self._settings = settings
        self._client = self._build_client()

    def upsert_chunks(
        self,
        chunks: list[PreparedConversationChunk],
        vectors: list[list[float]],
    ) -> None:
        if not chunks:
            return
        if len(chunks) != len(vectors):
            raise RuntimeError("Vector count must match prepared chunk count")

        client = self._get_client()
        self._ensure_collection(client, vector_size=len(vectors[0]))

        try:
            from qdrant_client.http.models import PointStruct
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is required for vector memory storage"
            ) from exc

        points = [
            PointStruct(
                id=prepared.chunk.chunk_id,
                vector=vector,
                payload=prepared.payload
                | {"text_for_embedding": prepared.text_for_embedding},
            )
            for prepared, vector in zip(chunks, vectors, strict=True)
        ]
        client.upsert(
            collection_name=self._settings.collection_name,
            points=points,
            wait=True,
        )
        logger.info(
            "vector_store.upsert.completed",
            {
                "collection": self._settings.collection_name,
                "chunk_count": len(chunks),
            },
        )

    def search_chunks(
        self,
        *,
        query_vector: list[float],
        limit: int,
    ) -> list[dict[str, object]]:
        client = self._get_client()
        search_result = client.search(
            collection_name=self._settings.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        logger.info(
            "vector_store.search.completed",
            {
                "collection": self._settings.collection_name,
                "limit": limit,
                "result_count": len(search_result),
            },
        )
        return [
            point.payload
            for point in search_result
            if isinstance(point.payload, dict)
        ]

    def _ensure_collection(self, client, *, vector_size: int) -> None:
        try:
            from qdrant_client.http.models import Distance, VectorParams
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is required for vector memory storage"
            ) from exc

        existing = {
            collection.name for collection in client.get_collections().collections
        }
        if self._settings.collection_name in existing:
            logger.debug(
                "vector_store.collection.exists",
                {
                    "collection": self._settings.collection_name,
                    "qdrant_url": self._settings.url,
                },
            )
            return

        client.create_collection(
            collection_name=self._settings.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(
            "vector_store.collection.created",
            {
                "collection": self._settings.collection_name,
                "qdrant_url": self._settings.url,
                "vector_size": vector_size,
                "distance": "cosine",
            },
        )

    def _get_client(self):
        return self._client

    def _build_client(self):
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is required for vector memory storage"
            ) from exc

        return QdrantClient(
            url=self._settings.url,
            trust_env=False,
        )


_STORE_CACHE: dict[QdrantSettings, QdrantConversationVectorStore] = {}
_STORE_LOCK = threading.Lock()


def build_qdrant_vector_store(settings: QdrantSettings) -> QdrantConversationVectorStore:
    cached = _STORE_CACHE.get(settings)
    if cached is not None:
        return cached

    with _STORE_LOCK:
        cached = _STORE_CACHE.get(settings)
        if cached is not None:
            return cached

        instance = QdrantConversationVectorStore(settings)
        _STORE_CACHE[settings] = instance
        return instance
