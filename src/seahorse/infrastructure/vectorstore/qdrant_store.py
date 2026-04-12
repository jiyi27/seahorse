from __future__ import annotations

import threading
from dataclasses import dataclass

from seahorse import logger
from seahorse.ingest.models import PreparedVectorRecord

SEARCH_METHOD_NAME = "search"
QUERY_POINTS_METHOD_NAME = "query_points"


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
        chunks: list[PreparedVectorRecord],
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
                id=prepared.record_id,
                vector=vector,
                payload=prepared.payload,
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
        search_result = self._run_search(
            client,
            query_vector=query_vector,
            limit=limit,
        )
        points = self._extract_search_points(search_result)
        logger.info(
            "vector_store.search.completed",
            {
                "collection": self._settings.collection_name,
                "limit": limit,
                "result_count": len(points),
            },
        )
        return [
            point.payload
            for point in points
            if isinstance(point.payload, dict)
        ]

    def check_connection(self) -> None:
        self._get_client().get_collections()

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

    def _run_search(
        self,
        client,
        *,
        query_vector: list[float],
        limit: int,
    ):
        search_method = getattr(client, SEARCH_METHOD_NAME, None)
        if callable(search_method):
            return search_method(
                collection_name=self._settings.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

        query_points_method = getattr(client, QUERY_POINTS_METHOD_NAME, None)
        if callable(query_points_method):
            return query_points_method(
                collection_name=self._settings.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

        raise RuntimeError(
            "qdrant-client does not expose a supported vector search method"
        )

    def _extract_search_points(self, search_result) -> list[object]:
        if isinstance(search_result, list):
            return search_result

        points = getattr(search_result, "points", None)
        if isinstance(points, list):
            return points

        raise RuntimeError("Unexpected qdrant search response shape")

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
