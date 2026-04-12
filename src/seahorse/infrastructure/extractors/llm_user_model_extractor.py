from __future__ import annotations

from pathlib import Path

from seahorse.domain.models import ConversationInput, UserModel, UserModelPatch
from seahorse.infrastructure.extractors.user_model_patch_parser import (
    UserModelPatchParser,
)
from seahorse.infrastructure.extractors.user_model_prompt_builder import (
    UserModelPromptBuilder,
)
from seahorse.infrastructure.providers.base import LLMProvider


class LLMUserModelExtractor:
    def __init__(
        self,
        provider: LLMProvider,
        prompt_path: Path,
        prompt_builder: UserModelPromptBuilder | None = None,
        patch_parser: UserModelPatchParser | None = None,
    ) -> None:
        self._provider = provider
        self._prompt_path = prompt_path
        self._prompt_builder = prompt_builder or UserModelPromptBuilder()
        self._patch_parser = patch_parser or UserModelPatchParser()

    def extract(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
    ) -> UserModelPatch:
        system_prompt = self._prompt_path.read_text(encoding="utf-8").strip()
        user_prompt = self._build_user_prompt(conversation, current_user_model)
        raw_output = self._provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return self._patch_parser.parse(raw_output)

    def _build_user_prompt(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
    ) -> str:
        return self._prompt_builder.build(conversation, current_user_model)
