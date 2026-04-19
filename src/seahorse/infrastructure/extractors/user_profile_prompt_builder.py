from __future__ import annotations

import json

from seahorse.domain.models import ConversationInput, FactItem, Message, TextItem, UserProfile


class UserProfilePromptBuilder:
    def build(
        self,
        conversation: ConversationInput,
        current_user_profile: UserProfile | None,
    ) -> str:
        current_profile_payload = self._build_current_profile_payload(current_user_profile)
        conversation_content = self._render_conversation(conversation)
        return (
            "Current user profile:\n"
            f"{json.dumps(current_profile_payload, ensure_ascii=False, indent=2)}\n\n"
            "Conversation input:\n"
            f"{conversation_content}\n"
        )

    def _build_current_profile_payload(
        self, current_user_profile: UserProfile | None
    ) -> dict[str, object]:
        if current_user_profile is None:
            return {
                "summary": "",
                "facts": [],
                "preferences": [],
                "constraints": [],
            }

        return {
            "summary": current_user_profile.summary,
            "facts": self._render_items(current_user_profile.facts),
            "preferences": self._render_text_items(current_user_profile.preferences),
            "constraints": self._render_text_items(current_user_profile.constraints),
        }

    @staticmethod
    def _render_items(items: list[FactItem]) -> list[dict[str, str]]:
        return [
            {"id": item.id, "category": item.category, "text": item.text}
            for item in items
        ]

    @staticmethod
    def _render_text_items(items: list[TextItem]) -> list[dict[str, str]]:
        return [{"id": item.id, "text": item.text} for item in items]

    def _render_conversation(self, conversation: ConversationInput) -> str:
        if conversation.content:
            return conversation.content.strip()
        rendered_messages: list[str] = []
        for message in conversation.messages:
            if message.role != "user":
                continue
            rendered_messages.append(self._render_message(message))
        return "\n".join(rendered_messages).strip()

    @staticmethod
    def _render_message(message: Message) -> str:
        return f"[{message.role}] {message.text.strip()}"
