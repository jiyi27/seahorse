from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import RecallContext
from seahorse.domain.repositories import PersonaRepository, UserModelRepository


class RecallService:
    def __init__(
        self,
        persona_repository: PersonaRepository,
        user_model_repository: UserModelRepository,
    ) -> None:
        self._persona_repository = persona_repository
        self._user_model_repository = user_model_repository

    def recall(self) -> RecallContext:
        logger.debug("recall.started", {})
        context = RecallContext(
            persona=self._persona_repository.load(),
            user_model=self._user_model_repository.load(),
        )
        logger.debug(
            "recall.completed",
            {
                "has_user_model": context.user_model is not None,
                "persona_len": len(context.persona.content),
            },
        )
        return context
