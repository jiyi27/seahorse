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
        blocks = build_conversation_blocks(conversation)
        prepared_records = self._prepare_records(blocks)
        if not prepared_records:
            return

        vectors = self._embedding_model.embed_documents(
            [prepared.text_for_embedding for prepared in prepared_records]
        )
        self._vector_store.upsert_chunks(prepared_records, vectors)

    def _prepare_records(self, blocks) -> list[PreparedVectorRecord]:
        prepared_records: list[PreparedVectorRecord] = []
        for block in blocks:
            prepared_records.extend(build_child_chunks(block))
        return prepared_records
