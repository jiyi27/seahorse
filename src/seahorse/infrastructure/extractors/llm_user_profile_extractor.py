from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from seahorse import logger
from seahorse.domain.models import (
    ConversationInput,
    FactItem,
    Message,
    TextItem,
    UserProfile,
    UserProfilePatch,
)
from seahorse.infrastructure.providers.base import LLMProvider


class LLMUserProfileExtractor:
    def __init__(
        self,
        provider: LLMProvider,
        prompt_path: Path,
    ) -> None:
        self._provider = provider
        self._prompt_path = prompt_path

    def extract(
        self,
        conversation: ConversationInput,
        current_user_profile: UserProfile | None,
    ) -> UserProfilePatch:
        system_prompt = self._prompt_path.read_text(encoding="utf-8").strip()
        user_prompt = self._build_user_prompt(conversation, current_user_profile)
        raw_output = self._provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return self._parse_patch(raw_output)

    def _build_user_prompt(
        self,
        conversation: ConversationInput,
        current_user_profile: UserProfile | None,
    ) -> str:
        current_profile_payload = self._build_current_profile_payload(
            current_user_profile
        )
        conversation_content = self._render_conversation(conversation)
        return (
            "Current user profile:\n"
            f"{json.dumps(current_profile_payload, ensure_ascii=False, indent=2)}\n\n"
            "Conversation input:\n"
            f"{conversation_content}\n"
        )

    def _build_current_profile_payload(
        self,
        current_user_profile: UserProfile | None,
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
            "facts": self._render_fact_items(current_user_profile.facts),
            "preferences": self._render_text_items(current_user_profile.preferences),
            "constraints": self._render_text_items(current_user_profile.constraints),
        }

    @staticmethod
    def _render_fact_items(items: list[FactItem]) -> list[dict[str, str]]:
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

    def _parse_patch(self, raw_output: str) -> UserProfilePatch:
        normalized = raw_output.strip()
        if normalized.startswith("```"):
            normalized = self._strip_code_fence(normalized)

        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError as exc:
            logger.error("extractor.output.invalid_json", {}, exc=exc)
            raise RuntimeError("LLM extractor returned invalid JSON") from exc

        try:
            return UserProfilePatch.model_validate(payload)
        except ValidationError as exc:
            logger.error("extractor.output.invalid_schema", {}, exc=exc)
            raise RuntimeError("LLM extractor returned an invalid patch payload") from exc

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        lines = content.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return content
