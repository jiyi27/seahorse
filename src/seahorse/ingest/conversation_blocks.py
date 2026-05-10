from __future__ import annotations

from seahorse.domain.models import ConversationInput, Message
from seahorse.ingest.models import ConversationBlock


BLOCK_MESSAGE_ROLES = {"user", "assistant", "tool"}


def build_conversation_blocks(
    conversation: ConversationInput,
) -> list[ConversationBlock]:
    messages = _normalize_conversation_messages(conversation)
    if not messages:
        return []

    blocks: list[ConversationBlock] = []
    current_messages: list[Message] = []

    for message in messages:
        if message.role not in BLOCK_MESSAGE_ROLES:
            continue

        if message.role == "user":
            # A new user message starts a new block. Any accumulated assistant/tool
            # context belongs to the previous user turn, so flush it first.
            if current_messages:
                blocks.append(ConversationBlock(messages=current_messages))
            current_messages = [message]
            continue

        # Ignore any leading assistant/tool messages before the first user turn.
        # For example, assistant -> tool -> user becomes a block starting at user,
        # so the leading assistant/tool messages are not vectorized or stored.
        if not current_messages:
            continue

        current_messages.append(message)

    if current_messages:
        blocks.append(ConversationBlock(messages=current_messages))
    return blocks


def _normalize_conversation_messages(conversation: ConversationInput) -> list[Message]:
    if conversation.messages:
        return conversation.messages
    if conversation.content is None:
        return []
    return [Message(role="user", text=conversation.content)]
