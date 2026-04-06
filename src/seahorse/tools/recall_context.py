from __future__ import annotations

from seahorse.application.recall_service import RecallService
from seahorse.application.user_model_renderer import UserModelRenderer
from seahorse.tools.contracts import (
    RECALL_CONTEXT_UNAVAILABLE_HINT,
    RecallContextSuccess,
    RecallContextResult,
    internal_error,
)


def recall_context(
    service: RecallService,
    renderer: UserModelRenderer,
) -> RecallContextResult:
    try:
        context = service.recall()
    except RuntimeError as exc:
        return internal_error(str(exc), RECALL_CONTEXT_UNAVAILABLE_HINT)

    rendered_user_model = None
    if context.user_model is not None:
        rendered_user_model = renderer.render_markdown(context.user_model) or None

    payload: RecallContextSuccess = {
        "success": True,
        "persona": context.persona.content,
        "user_model": rendered_user_model,
    }
    return payload
