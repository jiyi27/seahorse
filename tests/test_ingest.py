from __future__ import annotations

from seahorse.domain.models import ConversationInput, Message
from seahorse.ingest.block_content import build_block_content
from seahorse.ingest.child_chunks import build_child_chunks
from seahorse.ingest.conversation_blocks import build_conversation_blocks
from seahorse.ingest.ids import build_child_chunk_id, build_parent_block_id
from seahorse.ingest.vector_fields import CONTENT, EMBEDDING_TEXT, PARENT_BLOCK_ID


def test_build_conversation_blocks_groups_messages_by_user_turn() -> None:
    conversation = ConversationInput(
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

    assert len(blocks) == 2
    assert [len(block.messages) for block in blocks] == [4, 2]


def test_build_conversation_blocks_creates_single_block_for_content_only_input() -> None:
    conversation = ConversationInput(
        content="Remember this preference.",
    )

    blocks = build_conversation_blocks(conversation)

    assert len(blocks) == 1
    assert blocks[0].messages == [Message(role="user", text="Remember this preference.")]


def test_build_block_content_preserves_user_assistant_and_tool_roles() -> None:
    conversation = ConversationInput(
        messages=[
            Message(role="system", text="System prompt"),
            Message(role="user", text="I went home today."),
            Message(role="assistant", text="You were at school this morning."),
            Message(role="tool", text='{"source":"calendar"}'),
        ],
    )

    block = build_conversation_blocks(conversation)[0]

    assert build_block_content(block) == (
        "[user]\nI went home today.\n\n"
        "[assistant]\nYou were at school this morning.\n\n"
        '[tool]\n{"source":"calendar"}'
    )


def test_parent_and_child_ids_are_stable() -> None:
    content = "[user]\nI went home today.\n\n[assistant]\nYou were at school this morning."
    parent_block_id = build_parent_block_id(content)

    assert parent_block_id == build_parent_block_id(content)
    assert build_child_chunk_id(
        parent_block_id=parent_block_id,
        child_index=0,
        embedding_text="I went home today.",
    ) == build_child_chunk_id(
        parent_block_id=parent_block_id,
        child_index=0,
        embedding_text="I went home today.",
    )


def test_build_child_chunks_creates_one_child_per_user_and_assistant_message() -> None:
    conversation = ConversationInput(
        messages=[
            Message(role="system", text="System prompt"),
            Message(role="user", text="I went home today."),
            Message(role="assistant", text="You were at school this morning."),
            Message(role="tool", text='{"source":"calendar"}'),
        ],
    )

    block = build_conversation_blocks(conversation)[0]
    child_chunks = build_child_chunks(block)

    assert [child.text_for_embedding for child in child_chunks] == [
        "I went home today.",
        "You were at school this morning.",
    ]
    assert child_chunks[0].payload[EMBEDDING_TEXT] == "I went home today."
    assert child_chunks[1].payload[EMBEDDING_TEXT] == "You were at school this morning."
    assert child_chunks[0].payload[PARENT_BLOCK_ID] == child_chunks[1].payload[PARENT_BLOCK_ID]
    assert child_chunks[0].payload[CONTENT] == (
        "[user]\nI went home today.\n\n"
        "[assistant]\nYou were at school this morning.\n\n"
        '[tool]\n{"source":"calendar"}'
    )
