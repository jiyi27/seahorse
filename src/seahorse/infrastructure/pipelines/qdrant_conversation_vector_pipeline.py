from __future__ import annotations

from seahorse.domain.models import ConversationInput
from seahorse.ingest.child_chunks import build_child_chunks
from seahorse.ingest.conversation_blocks import build_conversation_blocks
from seahorse.ingest.models import PreparedVectorRecord


class QdrantConversationVectorPipeline:
    def __init__(self, embedding_model, vector_store) -> None:
        self._embedding_model = embedding_model
        self._vector_store = vector_store

    def process(self, conversation: ConversationInput) -> None:
        # Step 1: Split the conversation into blocks. Each block is a slice of messages
        # anchored at a user message, e.g. [user, assistant] or [user, assistant, tool].
        blocks = build_conversation_blocks(conversation)

        # Step 2: Expand each block into child chunks — one per user/assistant message.
        # Each chunk stores the full block content in its payload for retrieval later.
        prepared_records = self._prepare_records(blocks)
        if not prepared_records:
            return

        # Step 3: Embed all chunk texts in a single batch call.
        vectors = self._embedding_model.embed_documents(
            [prepared.text_for_embedding for prepared in prepared_records]
        )

        # Step 4: Upsert chunks and their vectors into Qdrant.
        # Upsert is idempotent — re-ingesting the same conversation is safe.
        self._vector_store.upsert_chunks(prepared_records, vectors)

    @staticmethod
    def _prepare_records(blocks) -> list[PreparedVectorRecord]:
        prepared_records: list[PreparedVectorRecord] = []
        for block in blocks:
            prepared_records.extend(build_child_chunks(block))
        return prepared_records
