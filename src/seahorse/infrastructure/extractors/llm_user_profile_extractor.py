from __future__ import annotations

from pathlib import Path

from seahorse.domain.models import ConversationInput, UserProfile, UserProfilePatch
from seahorse.infrastructure.extractors.user_profile_patch_parser import (
    UserProfilePatchParser,
)
from seahorse.infrastructure.extractors.user_profile_prompt_builder import (
    UserProfilePromptBuilder,
)
from seahorse.infrastructure.providers.base import LLMProvider


class LLMUserModelExtractor:
    def __init__(
        self,
        provider: LLMProvider,
        prompt_path: Path,
        prompt_builder: UserProfilePromptBuilder | None = None,
        patch_parser: UserProfilePatchParser | None = None,
    ) -> None:
        self._provider = provider
        self._prompt_path = prompt_path
        self._prompt_builder = prompt_builder or UserProfilePromptBuilder()
        self._patch_parser = patch_parser or UserProfilePatchParser()

    def extract(
        self,
        conversation: ConversationInput,
        current_user_model: UserProfile | None,
    ) -> UserProfilePatch:
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
        current_user_model: UserProfile | None,
    ) -> str:
        return self._prompt_builder.build(conversation, current_user_model)
