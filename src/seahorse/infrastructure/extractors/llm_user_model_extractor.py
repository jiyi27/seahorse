from __future__ import annotations

from pathlib import Path

from seahorse import logger
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
        logger.info(
            "extractor.extract.started",
            {
                "source": conversation.source,
                "session_id": conversation.session_id,
                "has_user_model": current_user_model is not None,
            },
        )
        system_prompt = self._prompt_path.read_text(encoding="utf-8").strip()
        user_prompt = self._build_user_prompt(conversation, current_user_model)
        raw_output = self._provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        logger.debug(
            "extractor.llm_output.received",
            {
                "raw_output": raw_output,
                "raw_output_len": len(raw_output),
                "has_code_fence": raw_output.strip().startswith("```"),
            },
        )
        patch = self._patch_parser.parse(raw_output)
        logger.info(
            "extractor.extract.succeeded",
            {
                "summary_updated": bool(patch.summary.strip()),
                "facts_add": len(patch.facts_to_add),
                "facts_remove": len(patch.fact_ids_to_remove),
                "prefs_add": len(patch.preferences_to_add),
                "prefs_remove": len(patch.preference_ids_to_remove),
                "constraints_add": len(patch.constraints_to_add),
                "constraints_remove": len(patch.constraint_ids_to_remove),
            },
        )
        return patch

    def _build_user_prompt(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
    ) -> str:
        return self._prompt_builder.build(conversation, current_user_model)
