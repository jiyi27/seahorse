from __future__ import annotations

from seahorse.domain.models import UserModel
from seahorse.domain.repositories import UserModelRepository


class RecallService:
    def __init__(self, user_model_repository: UserModelRepository) -> None:
        self._user_model_repository = user_model_repository

    def get_user_model(self) -> UserModel | None:
        return self._user_model_repository.load()
