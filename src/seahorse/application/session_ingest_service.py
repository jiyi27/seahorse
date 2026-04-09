from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import ConversationInput, SessionIngestResult

from .user_profile_ingest_service import UserProfileIngestService


class SessionIngestService:
    def __init__(
        self,
        user_profile_ingest_service: UserProfileIngestService,
    ) -> None:
        self._user_profile_ingest_service = user_profile_ingest_service

    def ingest(self, conversation: ConversationInput) -> SessionIngestResult:
        logger.info(
            "session_ingest.started",
            {
                "source": conversation.source,
                "session_id": conversation.session_id,
            },
        )
        result = self._user_profile_ingest_service.ingest(conversation)
        logger.info(
            "session_ingest.completed",
            {
                "user_model_updated": result.user_model_updated,
            },
        )
        return SessionIngestResult(user_model_updated=result.user_model_updated)
