from __future__ import annotations

from seahorse.domain.models import ConversationInput
from seahorse.ingest.block_content import build_block_content
from seahorse.ingest.conversation_blocks import build_conversation_blocks
from seahorse.ingest.ids import build_child_chunk_id, build_parent_block_id
from seahorse.ingest.models import ConversationBlock, PreparedVectorRecord
from seahorse.ingest.vector_fields import CONTENT, EMBEDDING_TEXT, PARENT_BLOCK_ID


EMBEDDING_ROLES = {"user", "assistant"}


def build_conversation_chunks(
    conversation: ConversationInput,
) -> list[PreparedVectorRecord]:
    chunks: list[PreparedVectorRecord] = []
    for block in build_conversation_blocks(conversation):
        chunks.extend(build_child_chunks(block))
    return chunks


def build_child_chunks(block: ConversationBlock) -> list[PreparedVectorRecord]:
    content = build_block_content(block)
    if not content:
        return []

    parent_block_id = build_parent_block_id(content)
    records: list[PreparedVectorRecord] = []
    child_index = 0
    for message in block.messages:
        if message.role not in EMBEDDING_ROLES:
            continue
        embedding_text = message.text.strip()
        if not embedding_text:
            continue
        records.append(
            PreparedVectorRecord(
                record_id=build_child_chunk_id(
                    parent_block_id=parent_block_id,
                    child_index=child_index,
                    embedding_text=embedding_text,
                ),
                text_for_embedding=embedding_text,
                payload={
                    PARENT_BLOCK_ID: parent_block_id,
                    EMBEDDING_TEXT: embedding_text,
                    CONTENT: content,
                },
            )
        )
        child_index += 1
    return records
