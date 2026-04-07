from __future__ import annotations

from seahorse.application.recall_service import RecallService
from seahorse.tools.contracts import GetPersonaResult, GetPersonaSuccess, internal_error
from seahorse.tools.tool_hints import PERSONA_UNAVAILABLE_HINT


def get_persona(service: RecallService) -> GetPersonaResult:
    try:
        persona = service.get_persona()
    except RuntimeError as exc:
        return internal_error(str(exc), PERSONA_UNAVAILABLE_HINT)

    payload: GetPersonaSuccess = {
        "success": True,
        "content": persona.content,
    }
    return payload
