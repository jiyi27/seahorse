from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from seahorse.domain.models import MessageRole, MemorySearchSourceType

type ToolErrorType = Literal["internal_error"]


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
