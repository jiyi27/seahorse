from __future__ import annotations

from seahorse.domain.models import ConversationInput, Message
from seahorse.infrastructure.pipelines.qdrant_conversation_vector_pipeline import (
    QdrantConversationVectorPipeline,
)


class FakeEmbeddingModel:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[0.1, 0.2] for _ in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.calls: list[tuple[list, list[list[float]]]] = []

    def upsert_chunks(self, chunks, vectors: list[list[float]]) -> None:
        self.calls.append((chunks, vectors))


def test_qdrant_conversation_vector_pipeline_embeds_clean_text_and_stores_payload() -> None:
    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore()
    pipeline = QdrantConversationVectorPipeline(
        embedding_model=embedding_model,
        vector_store=vector_store,
        chunk_min_characters=1,
        chunk_max_characters=1000,
    )

    pipeline.process(
        ConversationInput(
            source="http",
            session_id="session-1",
            messages=[
                Message(role="system", text="system prompt"),
                Message(role="user", text="remember i prefer concise answers"),
                Message(role="assistant", text="noted"),
                Message(role="tool", text='{"status":"stored"}'),
            ],
        )
    )

    assert embedding_model.calls == [
        [
            "[user]\nremember i prefer concise answers\n\n[assistant]\nnoted",
        ]
    ]
    assert len(vector_store.calls) == 1
    prepared_chunks, vectors = vector_store.calls[0]
    assert vectors == [[0.1, 0.2]]
    assert prepared_chunks[0].payload["messages"] == [
        {"role": "user", "text": "remember i prefer concise answers"},
        {"role": "assistant", "text": "noted"},
        {"role": "tool", "text": '{"status":"stored"}'},
    ]


def test_qdrant_conversation_vector_pipeline_skips_chunks_without_embedding_text() -> None:
    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore()
    pipeline = QdrantConversationVectorPipeline(
        embedding_model=embedding_model,
        vector_store=vector_store,
        chunk_min_characters=1,
        chunk_max_characters=1000,
    )

    pipeline.process(
        ConversationInput(
            source="http",
            session_id="session-1",
            messages=[Message(role="system", text="system prompt only")],
        )
    )

    assert embedding_model.calls == []
    assert vector_store.calls == []
