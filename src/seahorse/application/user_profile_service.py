from __future__ import annotations

from seahorse.domain.models import UserProfile
from seahorse.domain.repositories import UserProfileRepository
from seahorse.tools.contracts import UserProfilePayload


class UserProfileService:
    def __init__(self, user_profile_repository: UserProfileRepository) -> None:
        self._user_profile_repository = user_profile_repository

    def get_user_model(self) -> UserProfile | None:
        return self._user_profile_repository.load()
