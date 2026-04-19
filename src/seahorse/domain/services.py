from __future__ import annotations

from typing import Protocol

from seahorse.domain.models import ConversationInput, UserProfile, UserProfilePatch


class UserProfileExtractor(Protocol):
    def extract(
        self,
        conversation: ConversationInput,
        current_user_profile: UserProfile | None,
    ) -> UserProfilePatch: ...


class ConversationVectorPipeline(Protocol):
    def process(self, conversation: ConversationInput) -> None: ...
