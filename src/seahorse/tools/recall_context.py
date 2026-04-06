from __future__ import annotations

from seahorse.application.recall_service import RecallService
from seahorse.tools.contracts import (
    RECALL_CONTEXT_UNAVAILABLE_HINT,
    RecallContextResult,
    internal_error,
)


def recall_context(service: RecallService) -> RecallContextResult:
    try:
        context = service.recall()
    except RuntimeError as exc:
        return internal_error(str(exc), RECALL_CONTEXT_UNAVAILABLE_HINT)

    return {
        "success": True,
        "core_rule": context.core_rule.content,
        "user_model": context.user_model.content if context.user_model else None,
    }
