from __future__ import annotations

from hashlib import sha1

from seahorse.domain.models import Message
from seahorse.ingest.constants import (
    CHUNK_VERSION,
    DEFAULT_MAX_CHUNK_CHARACTERS,
    DEFAULT_MIN_CHUNK_CHARACTERS,
    SESSIONLESS_CHUNK_NAMESPACE,
)
from seahorse.ingest.models import ConversationBlock, ConversationChunk


def build_conversation_chunks(
    blocks: list[ConversationBlock],
    *,
    max_characters: int = DEFAULT_MAX_CHUNK_CHARACTERS,
    min_characters: int = DEFAULT_MIN_CHUNK_CHARACTERS,
) -> list[ConversationChunk]:
    if not blocks:
        return []

    pending_blocks: list[ConversationBlock] = []
    pending_length = 0
    chunks: list[ConversationChunk] = []

    for block in blocks:
        block_length = _block_character_length(block)
        if pending_blocks and pending_length < min_characters and block_length >= min_characters:
            chunks.append(_build_chunk_from_blocks(pending_blocks, len(chunks)))
            pending_blocks = []
            pending_length = 0

        if pending_blocks and pending_length + block_length > max_characters:
            chunks.append(_build_chunk_from_blocks(pending_blocks, len(chunks)))
            pending_blocks = []
            pending_length = 0

        pending_blocks.append(block)
        pending_length += block_length

        if pending_length >= min_characters:
            chunks.append(_build_chunk_from_blocks(pending_blocks, len(chunks)))
            pending_blocks = []
            pending_length = 0

    if pending_blocks:
        chunks.append(_build_chunk_from_blocks(pending_blocks, len(chunks)))

    return chunks


def _block_character_length(block: ConversationBlock) -> int:
    return sum(len(message.text.strip()) for message in block.messages)


def _build_chunk_from_blocks(
    blocks: list[ConversationBlock],
    chunk_index: int,
) -> ConversationChunk:
    first = blocks[0]
    last = blocks[-1]
    messages: list[Message] = []
    for block in blocks:
        messages.extend(block.messages)

    return ConversationChunk(
        chunk_id=build_chunk_id(
            session_id=first.session_id,
            start_message_index=first.start_message_index,
            end_message_index=last.end_message_index,
            messages=messages,
        ),
        chunk_index=chunk_index,
        session_id=first.session_id,
        start_message_index=first.start_message_index,
        end_message_index=last.end_message_index,
        messages=messages,
    )


def build_chunk_id(
    *,
    session_id: str | None,
    start_message_index: int,
    end_message_index: int,
    messages: list[Message],
) -> str:
    digest = sha1(
        "\n".join(_normalize_message_text(message) for message in messages).encode("utf-8")
    ).hexdigest()[:12]
    session_namespace = session_id or SESSIONLESS_CHUNK_NAMESPACE
    return (
        f"{session_namespace}:{start_message_index}:{end_message_index}:"
        f"{CHUNK_VERSION}:{digest}"
    )


def _normalize_message_text(message: Message) -> str:
    return f"{message.role}:{message.text.strip()}"
