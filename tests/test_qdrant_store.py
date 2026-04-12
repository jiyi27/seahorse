from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from seahorse import logger
from seahorse.ingest.models import PreparedVectorRecord
from seahorse.ingest.vector_fields import CONTENT, EMBEDDING_TEXT
from seahorse.infrastructure.vectorstore.qdrant_store import (
    QdrantConversationVectorStore,
    QdrantSettings,
)


class FakeLegacyClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return [SimpleNamespace(payload={"content": "legacy"})]


class FakeModernClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def query_points(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(points=[SimpleNamespace(payload={"content": "modern"})])


class FakeUpsertClient:
    def __init__(self) -> None:
        self.upsert_calls: list[dict[str, object]] = []

    def get_collections(self):
        return SimpleNamespace(collections=[SimpleNamespace(name="conversation-memory")])

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)


class FakePointStruct:
    def __init__(self, id: str, vector: list[float], payload: dict[str, object]) -> None:
        self.id = id
        self.vector = vector
        self.payload = payload


def build_store_with_client(client) -> QdrantConversationVectorStore:
    store = QdrantConversationVectorStore.__new__(QdrantConversationVectorStore)
    store._settings = QdrantSettings(
        url="http://localhost:6333",
        collection_name="conversation-memory",
    )
    store._client = client
    return store


def test_search_chunks_uses_legacy_search_api_when_available() -> None:
    client = FakeLegacyClient()
    store = build_store_with_client(client)

    payloads = store.search_chunks(query_vector=[0.1, 0.2], limit=3)

    assert payloads == [{"content": "legacy"}]
    assert client.calls == [
        {
            "collection_name": "conversation-memory",
            "query_vector": [0.1, 0.2],
            "limit": 3,
            "with_payload": True,
            "with_vectors": False,
        }
    ]


def test_search_chunks_falls_back_to_query_points_api() -> None:
    client = FakeModernClient()
    store = build_store_with_client(client)

    payloads = store.search_chunks(query_vector=[0.1, 0.2], limit=3)

    assert payloads == [{"content": "modern"}]
    assert client.calls == [
        {
            "collection_name": "conversation-memory",
            "query": [0.1, 0.2],
            "limit": 3,
            "with_payload": True,
            "with_vectors": False,
        }
    ]


def test_upsert_chunks_logs_each_chunk_payload_and_embedding(
    monkeypatch, tmp_path
) -> None:
    logger.configure(log_dir=tmp_path, level="debug")
    monkeypatch.setitem(
        sys.modules,
        "qdrant_client.http.models",
        SimpleNamespace(
            PointStruct=FakePointStruct,
            Distance=SimpleNamespace(COSINE="cosine"),
            VectorParams=lambda size, distance: {
                "size": size,
                "distance": distance,
            },
        ),
    )

    client = FakeUpsertClient()
    store = build_store_with_client(client)
    chunk = PreparedVectorRecord(
        record_id="chunk-1",
        text_for_embedding="remember this",
        payload={
            EMBEDDING_TEXT: "remember this",
            CONTENT: "[user]\nremember this",
        },
    )

    store.upsert_chunks([chunk], [[0.1, 0.2]])

    assert len(client.upsert_calls) == 1
    records = []
    for path in sorted(tmp_path.glob("*.debug.log")):
        for line in path.read_text(encoding="utf-8").splitlines():
            records.append(json.loads(line))

    chunk_record = next(
        record for record in records if record["topic"] == "vector_store.upsert.chunk"
    )
    assert chunk_record["data"] == {
        "record_id": "chunk-1",
        "embedding": [0.1, 0.2],
        "text_for_embedding": "remember this",
        "embedding_text": "remember this",
        "content": "[user]\nremember this",
    }
