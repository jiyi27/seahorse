from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import UserModel
from seahorse.domain.repositories import UserModelRepository


class RecallService:
    def __init__(self, user_model_repository: UserModelRepository) -> None:
        self._user_model_repository = user_model_repository

    def get_user_model(self) -> UserModel | None:
        logger.debug("recall.user_model.started", {})
        user_model = self._user_model_repository.load()
        logger.debug(
            "recall.user_model.completed",
            {
                "has_user_model": user_model is not None,
            },
        )
        return user_model
