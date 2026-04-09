from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import ConversationInput


class NoopConversationVectorPipeline:
    def process(self, conversation: ConversationInput) -> None:
        logger.debug(
            "conversation_vector_pipeline.skipped",
            {
                "source": conversation.source,
                "session_id": conversation.session_id,
            },
        )
        return None
