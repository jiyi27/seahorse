from __future__ import annotations

from seahorse import logger
from seahorse.domain.models import Persona, UserModel
from seahorse.domain.repositories import PersonaRepository, UserModelRepository


class RecallService:
    def __init__(
        self,
        persona_repository: PersonaRepository,
        user_model_repository: UserModelRepository,
    ) -> None:
        self._persona_repository = persona_repository
        self._user_model_repository = user_model_repository

    def get_persona(self) -> Persona:
        logger.debug("recall.persona.started", {})
        persona = self._persona_repository.load()
        logger.debug(
            "recall.persona.completed",
            {
                "persona_len": len(persona.content),
            },
        )
        return persona

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
