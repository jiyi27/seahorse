from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import ConversationInput
from seahorse.ingest.chunk_policy import build_conversation_chunks
from seahorse.ingest.conversation_blocks import build_conversation_blocks
from seahorse.ingest.embedding_text import build_embedding_text
from seahorse.ingest.models import PreparedConversationChunk
from seahorse.ingest.payloads import build_chunk_payload


class QdrantConversationVectorPipeline:
    def __init__(
        self,
        embedding_model,
        vector_store,
        *,
        chunk_min_characters: int,
        chunk_max_characters: int,
    ) -> None:
        self._embedding_model = embedding_model
        self._vector_store = vector_store
        self._chunk_min_characters = chunk_min_characters
        self._chunk_max_characters = chunk_max_characters

    def process(self, conversation: ConversationInput) -> None:
        logger.info(
            "conversation_vector_pipeline.started",
            {
                "source": conversation.source,
                "session_id": conversation.session_id,
            },
        )
        blocks = build_conversation_blocks(conversation)
        chunks = build_conversation_chunks(
            blocks,
            min_characters=self._chunk_min_characters,
            max_characters=self._chunk_max_characters,
        )
        prepared_chunks = self._prepare_chunks(chunks)
        if not prepared_chunks:
            logger.info(
                "conversation_vector_pipeline.skipped",
                {
                    "source": conversation.source,
                    "session_id": conversation.session_id,
                    "reason": "no_embedding_text",
                },
            )
            return

        vectors = self._embedding_model.embed_documents(
            [prepared.text_for_embedding for prepared in prepared_chunks]
        )
        self._vector_store.upsert_chunks(prepared_chunks, vectors)
        logger.info(
            "conversation_vector_pipeline.completed",
            {
                "session_id": conversation.session_id,
                "block_count": len(blocks),
                "chunk_count": len(chunks),
                "stored_chunk_count": len(prepared_chunks),
            },
        )

    def _prepare_chunks(self, chunks) -> list[PreparedConversationChunk]:
        prepared_chunks: list[PreparedConversationChunk] = []
        for chunk in chunks:
            text_for_embedding = build_embedding_text(chunk)
            if not text_for_embedding:
                continue
            prepared_chunks.append(
                PreparedConversationChunk(
                    chunk=chunk,
                    text_for_embedding=text_for_embedding,
                    payload=build_chunk_payload(chunk),
                )
            )
        return prepared_chunks
