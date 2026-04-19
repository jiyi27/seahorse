from __future__ import annotations

from seahorse.application.user_profile_merger import UserProfileMerger
from seahorse.domain.models import ConversationInput, IngestResult, UserProfilePatch
from seahorse.domain.repositories import UserProfileRepository
from seahorse.domain.services import UserProfileExtractor


class UserProfileIngestService:
    def __init__(
        self,
        user_model_repository: UserProfileRepository,
        extractor: UserProfileExtractor,
        merger: UserProfileMerger,
    ) -> None:
        self._user_model_repository = user_model_repository
        self._extractor = extractor
        self._merger = merger

    def ingest(self, conversation: ConversationInput) -> IngestResult:
        current_user_model = self._user_model_repository.load()
        extraction_conversation = self._build_extraction_conversation(conversation)
        if extraction_conversation is None:
            merged = self._merger.merge(current_user_model, UserProfilePatch())
            return IngestResult(
                user_profile=merged.user_profile,
                user_profile_updated=False,
            )

        patch = self._extractor.extract(extraction_conversation, current_user_model)
        merged = self._merger.merge(current_user_model, patch)
        merged_user_model = merged.user_profile

        if merged.changed:
            self._user_model_repository.save(merged_user_model)

        return IngestResult(
            user_profile=merged_user_model,
            user_profile_updated=merged.changed,
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
