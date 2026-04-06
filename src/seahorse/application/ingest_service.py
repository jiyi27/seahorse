from __future__ import annotations

from seahorse import logger
from seahorse.application.user_model_merger import UserModelMerger
from seahorse.domain.models import ConversationInput, IngestResult
from seahorse.domain.repositories import UserModelRepository
from seahorse.domain.services import EpisodePipeline, UserModelExtractor


class IngestService:
    def __init__(
        self,
        user_model_repository: UserModelRepository,
        extractor: UserModelExtractor,
        merger: UserModelMerger,
        episode_pipeline: EpisodePipeline,
    ) -> None:
        self._user_model_repository = user_model_repository
        self._extractor = extractor
        self._merger = merger
        self._episode_pipeline = episode_pipeline

    def ingest(self, conversation: ConversationInput) -> IngestResult:
        logger.info(
            "ingest.started",
            {
                "source": conversation.source,
                "session_id": conversation.session_id,
            },
        )
        current_user_model = self._user_model_repository.load()

        patch = self._extractor.extract(conversation, current_user_model)
        merged = self._merger.merge(current_user_model, patch)
        merged_user_model = merged.user_model

        logger.info(
            "ingest.patch.applied",
            {
                "user_model_updated": merged.changed,
                "version": merged_user_model.version,
            },
        )

        self._user_model_repository.save(merged_user_model)
        self._episode_pipeline.process(conversation)

        logger.info(
            "ingest.completed",
            {
                "user_model_updated": merged.changed,
                "version": merged_user_model.version,
            },
        )
        return IngestResult(
            user_model=merged_user_model,
            user_model_updated=merged.changed,
        )
