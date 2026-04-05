from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from seahorse.domain.models import (
    ConversationInput,
    CoreRule,
    Message,
    UserModel,
    UserModelPatch,
)
from seahorse.infrastructure.providers.base import LLMProvider


class LLMUserModelExtractor:
    def __init__(self, provider: LLMProvider, prompt_path: Path) -> None:
        self._provider = provider
        self._prompt_path = prompt_path

    def extract(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
        core_rule: CoreRule,
    ) -> UserModelPatch:
        system_prompt = self._prompt_path.read_text(encoding="utf-8").strip()
        user_prompt = self._build_user_prompt(conversation, current_user_model, core_rule)
        raw_output = self._provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return self._parse_output(raw_output)

    def _build_user_prompt(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
        core_rule: CoreRule,
    ) -> str:
        current_model_content = (
            current_user_model.content if current_user_model else "No user model yet."
        )
        conversation_content = self._render_conversation(conversation)
        return (
            "Core rule:\n"
            f"{core_rule.content.strip()}\n\n"
            "Current user model:\n"
            f"{current_model_content.strip()}\n\n"
            "Conversation input:\n"
            f"{conversation_content}\n"
        )

    def _render_conversation(self, conversation: ConversationInput) -> str:
        if conversation.content:
            return conversation.content.strip()
        rendered_messages: list[str] = []
        for message in conversation.messages:
            rendered_messages.append(self._render_message(message))
        return "\n".join(rendered_messages).strip()

    def _render_message(self, message: Message) -> str:
        return f"[{message.role}] {message.text.strip()}"

    def _parse_output(self, raw_output: str) -> UserModelPatch:
        normalized = raw_output.strip()
        if normalized.startswith("```"):
            normalized = self._strip_code_fence(normalized)

        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise RuntimeError("LLM extractor returned invalid JSON") from exc

        try:
            return UserModelPatch.model_validate(payload)
        except ValidationError as exc:
            raise RuntimeError("LLM extractor returned an invalid patch payload") from exc

    def _strip_code_fence(self, content: str) -> str:
        lines = content.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return content
