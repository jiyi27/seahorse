from __future__ import annotations

from seahorse.domain.models import ConversationInput
from seahorse.ingest.child_chunks import build_conversation_chunks


class QdrantConversationVectorPipeline:
    def __init__(self, embedding_model, vector_store) -> None:
        self._embedding_model = embedding_model
        self._vector_store = vector_store

    def process(self, conversation: ConversationInput) -> None:
        # Build vector chunks from user-anchored conversation blocks.
        # Each chunk embeds one user/assistant message and stores the full block
        # content in its payload for retrieval later.
        chunks = build_conversation_chunks(conversation)
        if not chunks:
            return

        # Embed all chunk texts in a single batch call.
        vectors = self._embedding_model.embed_documents(
            [chunk.text_for_embedding for chunk in chunks]
        )

        # Upsert is idempotent — re-ingesting the same conversation is safe.
        self._vector_store.upsert_chunks(chunks, vectors)
