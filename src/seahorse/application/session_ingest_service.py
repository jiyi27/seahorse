from __future__ import annotations

from seahorse.domain.models import ConversationInput, SessionIngestResult
from seahorse.domain.services import ConversationVectorPipeline

from .user_profile_ingest_service import UserProfileIngestService


class SessionIngestService:
    def __init__(
        self,
        user_profile_ingest_service: UserProfileIngestService,
        conversation_vector_pipeline: ConversationVectorPipeline,
    ) -> None:
        self._user_profile_ingest_service = user_profile_ingest_service
        self._conversation_vector_pipeline = conversation_vector_pipeline

    def ingest(self, conversation: ConversationInput) -> SessionIngestResult:
        result = self._user_profile_ingest_service.ingest(conversation)
        self._conversation_vector_pipeline.process(conversation)
        return SessionIngestResult(
            user_model_updated=result.user_model_updated,
            vector_pipeline_processed=True,
        )
