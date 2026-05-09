from __future__ import annotations

from seahorse.domain.models import ConversationInput, Message
from seahorse.ingest.models import ConversationBlock


def build_conversation_blocks(
    conversation: ConversationInput,
) -> list[ConversationBlock]:
    messages = _normalize_conversation_messages(conversation)
    if not messages:
        return []

    blocks: list[ConversationBlock] = []
    current_messages: list[Message] = []
    block_start_index = 0

    for index, message in enumerate(messages):
        if message.role == "user" and current_messages:
            blocks.append(
                ConversationBlock(
                    start_message_index=block_start_index,
                    end_message_index=index - 1,
                    messages=current_messages,
                )
            )
            current_messages = []
            block_start_index = index
        elif not current_messages:
            block_start_index = index

        current_messages.append(message)

    blocks.append(
        ConversationBlock(
            start_message_index=block_start_index,
            end_message_index=len(messages) - 1,
            messages=current_messages,
        )
    )
    return blocks


def _normalize_conversation_messages(conversation: ConversationInput) -> list[Message]:
    if conversation.messages:
        return conversation.messages
    if conversation.content is None:
        return []
    return [Message(role="user", text=conversation.content)]
