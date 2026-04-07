from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from seahorse.domain.models import MessageRole, MemorySearchSourceType

type ToolErrorType = Literal["internal_error"]

INGEST_RETRY_HINT = (
    "An internal error occurred. Retry up to 2 times; if still failing, stop and "
    "notify the user with the message above."
)
PERSONA_UNAVAILABLE_HINT = (
    "Persona unavailable. Do not guess your behavioral rules. Stop and notify "
    "the user."
)
USER_PROFILE_EMPTY_HINT = (
    "No user profile has been built yet. Proceed without personalization."
)
USER_PROFILE_UNAVAILABLE_HINT = (
    "User profile unavailable. Proceed without personalization. Do not halt."
)
SEARCH_MEMORY_HAS_RESULTS_HINT = (
    "These may or may not be what you're looking for - treat them as loose leads, "
    "not confirmed facts. If something looks relevant, bring it up naturally "
    "rather than announcing a search result. If you're unsure, ask casually. "
    "If two attempts don't land, let it go - tell the user you can't quite place "
    "it and move on."
)
SEARCH_MEMORY_NO_RESULTS_HINT = (
    "No matching memory was found for this query. Do not guess. You may tell the "
    "user you don't recall, or ask them directly what they are referring to."
)
SEARCH_MEMORY_FAILED_HINT = (
    "Memory search failed. Do not retry automatically. Proceed without recalled "
    "context."
)


class ToolFailure(TypedDict):
    success: Literal[False]
    error_type: ToolErrorType
    message: str
    hint: str


class GetPersonaSuccess(TypedDict):
    success: Literal[True]
    content: str


class UserProfileFactItem(TypedDict):
    id: str
    category: str
    text: str


class UserProfileTextItem(TypedDict):
    id: str
    text: str


class UserProfilePayload(TypedDict):
    summary: str
    facts: list[UserProfileFactItem]
    preferences: list[UserProfileTextItem]
    constraints: list[UserProfileTextItem]


class GetUserProfileSuccess(TypedDict):
    success: Literal[True]
    profile: UserProfilePayload | None
    hint: NotRequired[str]


class SearchMemoryResultItemPayload(TypedDict):
    id: str
    source_type: MemorySearchSourceType
    text: str


class SearchMemorySuccess(TypedDict):
    success: Literal[True]
    results: list[SearchMemoryResultItemPayload]
    hint: str


class IngestTurnSuccess(TypedDict):
    success: Literal[True]
    user_model_updated: bool


class ToolInputMessage(TypedDict):
    role: MessageRole
    text: str


type GetPersonaResult = GetPersonaSuccess | ToolFailure
type GetUserProfileResult = GetUserProfileSuccess | ToolFailure
type SearchMemoryResult = SearchMemorySuccess | ToolFailure
type IngestTurnResult = IngestTurnSuccess | ToolFailure


def internal_error(message: str, hint: str) -> ToolFailure:
    return {
        "success": False,
        "error_type": "internal_error",
        "message": message,
        "hint": hint,
    }
