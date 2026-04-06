from __future__ import annotations

from typing import Literal, TypedDict

from seahorse.domain.models import MessageRole

type ToolErrorType = Literal["internal_error"]

INGEST_RETRY_HINT = (
    "An internal error occurred. Retry up to 2 times; if still failing, stop and "
    "notify the user with the message above."
)
RECALL_CONTEXT_UNAVAILABLE_HINT = (
    "Memory context unavailable. Do not guess. Stop and notify the user."
)


class ToolFailure(TypedDict):
    success: Literal[False]
    error_type: ToolErrorType
    message: str
    hint: str


class RecallContextSuccess(TypedDict):
    success: Literal[True]
    persona: str
    user_model: str | None


class IngestTurnSuccess(TypedDict):
    success: Literal[True]
    user_model_updated: bool


class ToolInputMessage(TypedDict):
    role: MessageRole
    text: str


type RecallContextResult = RecallContextSuccess | ToolFailure
type IngestTurnResult = IngestTurnSuccess | ToolFailure


def internal_error(message: str, hint: str) -> ToolFailure:
    return {
        "success": False,
        "error_type": "internal_error",
        "message": message,
        "hint": hint,
    }
