from __future__ import annotations

from seahorse import logger
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.domain.models import ConversationInput, IngestResult, UserModelPatch
from seahorse.domain.repositories import UserModelRepository
from seahorse.domain.services import UserModelExtractor


class UserProfileIngestService:
    def __init__(
        self,
        user_model_repository: UserModelRepository,
        extractor: UserModelExtractor,
        merger: UserModelMerger,
    ) -> None:
        self._user_model_repository = user_model_repository
        self._extractor = extractor
        self._merger = merger

    def ingest(self, conversation: ConversationInput) -> IngestResult:
        logger.info(
            "user_profile_ingest.started",
            {
                "source": conversation.source,
                "session_id": conversation.session_id,
            },
        )
        current_user_model = self._user_model_repository.load()
        extraction_conversation = self._build_extraction_conversation(conversation)
        if extraction_conversation is None:
            logger.info(
                "user_profile_ingest.skipped",
                {
                    "source": conversation.source,
                    "session_id": conversation.session_id,
                    "reason": "no_user_content",
                },
            )
            merged = self._merger.merge(current_user_model, UserModelPatch())
            return IngestResult(
                user_model=merged.user_model,
                user_model_updated=False,
            )

        patch = self._extractor.extract(extraction_conversation, current_user_model)
        merged = self._merger.merge(current_user_model, patch)
        merged_user_model = merged.user_model

        logger.info(
            "user_profile_ingest.patch.applied",
            {
                "user_model_updated": merged.changed,
            },
        )

        if merged.changed:
            self._user_model_repository.save(merged_user_model)

        logger.info(
            "user_profile_ingest.completed",
            {
                "user_model_updated": merged.changed,
            },
        )
        return IngestResult(
            user_model=merged_user_model,
            user_model_updated=merged.changed,
        )

    def _build_extraction_conversation(
        self, conversation: ConversationInput
    ) -> ConversationInput | None:
        if conversation.content is not None:
            return conversation

        user_messages = [
            message for message in conversation.messages if message.role == "user"
        ]
        if not user_messages:
            return None

        return ConversationInput(
            source=conversation.source,
            session_id=conversation.session_id,
            messages=user_messages,
        )
