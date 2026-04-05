from __future__ import annotations

from seahorse.domain.models import ConversationInput


class NoopEpisodePipeline:
    def process(self, conversation: ConversationInput) -> None:
        return None
