from __future__ import annotations

from seahorse.domain.models import RecallContext
from seahorse.domain.repositories import CoreRuleRepository, UserModelRepository


class RecallService:
    def __init__(
        self,
        core_rule_repository: CoreRuleRepository,
        user_model_repository: UserModelRepository,
    ) -> None:
        self._core_rule_repository = core_rule_repository
        self._user_model_repository = user_model_repository

    def recall(self) -> RecallContext:
        return RecallContext(
            core_rule=self._core_rule_repository.load(),
            user_model=self._user_model_repository.load(),
        )
