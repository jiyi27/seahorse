from __future__ import annotations

from seahorse.domain.models import ConversationInput, Message
from seahorse.ingest.chunk_policy import build_conversation_chunks
from seahorse.ingest.conversation_blocks import build_conversation_blocks
from seahorse.ingest.embedding_text import build_embedding_text
from seahorse.ingest.payloads import build_chunk_payload


def test_build_conversation_blocks_groups_messages_by_user_turn() -> None:
    conversation = ConversationInput(
        source="http",
        session_id="session-1",
        messages=[
            Message(role="system", text="You are helpful."),
            Message(role="user", text="Hello"),
            Message(role="assistant", text="Hi there"),
            Message(role="tool", text='{"result":"ignored for embedding"}'),
            Message(role="assistant", text="I checked that for you."),
            Message(role="user", text="Thanks"),
            Message(role="assistant", text="You're welcome"),
        ],
    )

    blocks = build_conversation_blocks(conversation)

    assert [(block.start_message_index, block.end_message_index) for block in blocks] == [
        (0, 0),
        (1, 4),
        (5, 6),
    ]


def test_build_conversation_blocks_creates_single_block_for_content_only_input() -> None:
    conversation = ConversationInput(
        source="mcp",
        content="Remember this preference.",
        session_id="session-1",
    )

    blocks = build_conversation_blocks(conversation)

    assert len(blocks) == 1
    assert blocks[0].messages == [Message(role="user", text="Remember this preference.")]


def test_build_conversation_chunks_merges_short_adjacent_blocks_until_threshold() -> None:
    conversation = ConversationInput(
        source="http",
        session_id="session-1",
        messages=[
            Message(role="user", text="short"),
            Message(role="assistant", text="tiny"),
            Message(role="user", text="small"),
            Message(role="assistant", text="brief"),
            Message(role="user", text="This third block is long enough to flush the chunk."),
            Message(role="assistant", text="This response also adds more text."),
        ],
    )

    blocks = build_conversation_blocks(conversation)
    chunks = build_conversation_chunks(blocks, min_characters=20, max_characters=200)

    assert [(chunk.start_message_index, chunk.end_message_index) for chunk in chunks] == [
        (0, 3),
        (4, 5),
    ]
    assert chunks[0].chunk_id == build_conversation_chunks(
        blocks, min_characters=20, max_characters=200
    )[0].chunk_id


def test_build_embedding_text_only_uses_user_and_assistant_messages() -> None:
    conversation = ConversationInput(
        source="http",
        session_id="session-1",
        messages=[
            Message(role="system", text="System prompt"),
            Message(role="user", text="Need a memory system"),
            Message(role="assistant", text="Start with stable chunking"),
            Message(role="tool", text='{"status":"ok"}'),
        ],
    )

    chunk = build_conversation_chunks(build_conversation_blocks(conversation))[0]

    assert build_embedding_text(chunk) == (
        "[user]\nNeed a memory system\n\n"
        "[assistant]\nStart with stable chunking"
    )


def test_build_chunk_payload_preserves_full_messages_and_role_summaries() -> None:
    conversation = ConversationInput(
        source="http",
        session_id="session-1",
        messages=[
            Message(role="user", text="Please remember I prefer concise answers."),
            Message(role="assistant", text="Noted."),
            Message(role="tool", text='{"tool":"memory_write"}'),
        ],
    )

    chunk = build_conversation_chunks(build_conversation_blocks(conversation))[0]
    payload = build_chunk_payload(chunk)

    assert payload["session_id"] == "session-1"
    assert payload["roles_present"] == ["assistant", "tool", "user"]
    assert payload["user_text"] == "Please remember I prefer concise answers."
    assert payload["assistant_text"] == "Noted."
    assert payload["has_tool_messages"] is True
    assert payload["messages"] == [
        {
            "role": "user",
            "text": "Please remember I prefer concise answers.",
        },
        {
            "role": "assistant",
            "text": "Noted.",
        },
        {
            "role": "tool",
            "text": '{"tool":"memory_write"}',
        },
    ]
