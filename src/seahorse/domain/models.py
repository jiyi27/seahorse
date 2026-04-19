from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator
from seahorse.constants import APP_NAME, OPENROUTER_BASE_URL, OPENROUTER_PROVIDER


type MessageRole = Literal["system", "user", "assistant", "tool"]
type ConversationSource = Literal["mcp", "http"]
type FactCategory = Literal[
    "identity",
    "personality",
    "social",
    "interests",
    "values",
    "life_situation",
    "note",
]
type MemorySearchSourceType = Literal["fact", "preference", "constraint", "conversation"]


class FactItem(BaseModel):
    id: str
    category: FactCategory
    text: str


class TextItem(BaseModel):
    id: str
    text: str


class UserProfile(BaseModel):
    summary: str = ""
    facts: list[FactItem] = Field(default_factory=list)
    preferences: list[TextItem] = Field(default_factory=list)
    constraints: list[TextItem] = Field(default_factory=list)


class MemorySearchResultItem(BaseModel):
    id: str
    source_type: MemorySearchSourceType
    text: str


class Message(BaseModel):
    role: MessageRole
    text: str


class ConversationInput(BaseModel):
    source: ConversationSource
    content: str | None = None
    messages: list[Message] = Field(default_factory=list)
    session_id: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "ConversationInput":
        normalized_content = self.content.strip() if self.content is not None else None
        self.content = normalized_content or None

        has_content = self.content is not None
        has_messages = bool(self.messages)

        if has_content and has_messages:
            msg = "ConversationInput accepts either content or messages, not both"
            raise ValueError(msg)
        if not has_content and not has_messages:
            msg = "ConversationInput requires content or at least one message"
            raise ValueError(msg)
        return self


class FactPatchItem(BaseModel):
    category: FactCategory
    text: str


class UserProfilePatch(BaseModel):
    summary: str = ""
    facts_to_add: list[FactPatchItem] = Field(default_factory=list)
    fact_ids_to_remove: list[str] = Field(default_factory=list)
    preferences_to_add: list[str] = Field(default_factory=list)
    preference_ids_to_remove: list[str] = Field(default_factory=list)
    constraints_to_add: list[str] = Field(default_factory=list)
    constraint_ids_to_remove: list[str] = Field(default_factory=list)


class IngestResult(BaseModel):
    user_profile: UserProfile
    user_profile_updated: bool


class SessionIngestResult(BaseModel):
    user_profile_updated: bool
    vector_pipeline_processed: bool


class ProviderSettings(BaseModel):
    provider: Literal["openrouter"] = OPENROUTER_PROVIDER
    model: str
    api_key: str
    base_url: str = OPENROUTER_BASE_URL
    timeout_seconds: float = 60.0
    app_name: str | None = APP_NAME
    referer: str | None = None
