from __future__ import annotations

from seahorse.domain.models import MemorySearchResultItem
from seahorse.ingest.vector_fields import CONTENT, PARENT_BLOCK_ID
from seahorse.retrieval.conversation_recall import (
    ConversationParentHit,
    build_conversation_search_results,
    dedupe_conversation_parent_hits,
    render_conversation_parent_hit,
)
from seahorse.retrieval.result_rendering import render_vector_search_result
from seahorse.retrieval.vector_search_service import VectorSearchService


class FakeEmbeddingModel:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[0.3, 0.4] for _ in texts]


class FakeVectorStore:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[list[float], int]] = []

    def search_chunks(self, *, query_vector: list[float], limit: int) -> list[dict[str, object]]:
        self.calls.append((query_vector, limit))
        return self.payloads


def test_render_conversation_parent_hit_requires_parent_id_and_content() -> None:
    assert render_conversation_parent_hit({PARENT_BLOCK_ID: "block-1"}) is None
    assert render_conversation_parent_hit({CONTENT: "text"}) is None


def test_dedupe_conversation_parent_hits_keeps_first_hit_per_parent() -> None:
    deduped_hits = dedupe_conversation_parent_hits(
        [
            ConversationParentHit(parent_block_id="block-1", content="first"),
            ConversationParentHit(parent_block_id="block-1", content="second"),
            ConversationParentHit(parent_block_id="block-2", content="third"),
        ]
    )

    assert deduped_hits == [
        ConversationParentHit(parent_block_id="block-1", content="first"),
        ConversationParentHit(parent_block_id="block-2", content="third"),
    ]


def test_build_conversation_search_results_maps_hits_to_memory_results() -> None:
    assert build_conversation_search_results(
        [ConversationParentHit(parent_block_id="block-1", content="block text")]
    ) == [
        MemorySearchResultItem(
            id="block-1",
            source_type="conversation",
            text="block text",
        )
    ]


def test_render_vector_search_result_uses_parent_content() -> None:
    result = render_vector_search_result(
        {
            PARENT_BLOCK_ID: "block-1",
            CONTENT: "[user]\nI want memory.\n\n[assistant]\nWe discussed adding vector memory.",
        }
    )

    assert result == MemorySearchResultItem(
        id="block-1",
        source_type="conversation",
        text="[user]\nI want memory.\n\n[assistant]\nWe discussed adding vector memory.",
    )


def test_vector_search_service_embeds_query_dedupes_by_parent_block() -> None:
    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore(
        [
            {
                PARENT_BLOCK_ID: "block-1",
                CONTENT: "[user]\nI want memory.\n\n[assistant]\nWe discussed adding vector memory.",
            },
            {
                PARENT_BLOCK_ID: "block-1",
                CONTENT: "[user]\nI want memory.\n\n[assistant]\nWe discussed adding vector memory.",
            },
        ]
    )
    service = VectorSearchService(embedding_model, vector_store, top_k=5)

    results = service.search("vector memory")

    assert embedding_model.calls == [["vector memory"]]
    assert vector_store.calls == [([0.3, 0.4], 5)]
    assert results == [
        MemorySearchResultItem(
            id="block-1",
            source_type="conversation",
            text="[user]\nI want memory.\n\n[assistant]\nWe discussed adding vector memory.",
        )
    ]
