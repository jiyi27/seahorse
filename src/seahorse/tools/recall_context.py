from __future__ import annotations

from seahorse.application.recall_service import RecallService


def recall_context(service: RecallService) -> dict[str, str]:
    context = service.recall()
    return {
        "core_rule": context.core_rule.content,
        "user_model": context.user_model.content if context.user_model else "",
    }
