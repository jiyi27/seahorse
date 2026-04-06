from __future__ import annotations

from typing import Protocol

from seahorse.domain.models import ConversationInput, UserModel, UserModelPatch


class UserModelExtractor(Protocol):
    def extract(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
    ) -> UserModelPatch: ...


class EpisodePipeline(Protocol):
    def process(self, conversation: ConversationInput) -> None: ...
