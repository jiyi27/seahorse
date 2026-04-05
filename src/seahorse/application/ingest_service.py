from __future__ import annotations

from seahorse.application.user_model_merger import UserModelMerger
from seahorse.domain.models import ConversationInput, IngestResult
from seahorse.domain.repositories import CoreRuleRepository, UserModelRepository
from seahorse.domain.services import EpisodePipeline, UserModelExtractor


class IngestService:
    def __init__(
        self,
        core_rule_repository: CoreRuleRepository,
        user_model_repository: UserModelRepository,
        extractor: UserModelExtractor,
        merger: UserModelMerger,
        episode_pipeline: EpisodePipeline,
    ) -> None:
        self._core_rule_repository = core_rule_repository
        self._user_model_repository = user_model_repository
        self._extractor = extractor
        self._merger = merger
        self._episode_pipeline = episode_pipeline

    def ingest(self, conversation: ConversationInput) -> IngestResult:
        core_rule = self._core_rule_repository.load()
        current_user_model = self._user_model_repository.load()

        patch = self._extractor.extract(conversation, current_user_model, core_rule)
        merged_user_model = self._merger.merge(current_user_model, patch)

        self._user_model_repository.save(merged_user_model)
        self._episode_pipeline.process(conversation)

        was_updated = (
            current_user_model is None
            or current_user_model.content != merged_user_model.content
        )
        return IngestResult(
            user_model=merged_user_model,
            user_model_updated=was_updated,
        )
