from __future__ import annotations

from types import SimpleNamespace

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
