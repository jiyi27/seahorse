from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict

from pydantic import BaseModel, Field, model_validator
from seahorse.constants import APP_NAME, OPENROUTER_BASE_URL, OPENROUTER_PROVIDER


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


type MessageRole = Literal["system", "user", "assistant", "tool"]
type ConversationSource = Literal["mcp", "http"]


class CoreRule(BaseModel):
    content: str
    updated_at: datetime = Field(default_factory=utc_now)


class UserModel(BaseModel):
    content: str
    updated_at: datetime = Field(default_factory=utc_now)
    version: int = 1


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
        if not self.content and not self.messages:
            msg = "ConversationInput requires content or at least one message"
            raise ValueError(msg)
        return self


class UserModelPatch(BaseModel):
    summary: str = ""
    facts_to_add: list[str] = Field(default_factory=list)
    facts_to_remove: list[str] = Field(default_factory=list)
    preferences_to_add: list[str] = Field(default_factory=list)
    preferences_to_remove: list[str] = Field(default_factory=list)
    constraints_to_add: list[str] = Field(default_factory=list)
    constraints_to_remove: list[str] = Field(default_factory=list)


class RecallContext(BaseModel):
    core_rule: CoreRule
    user_model: UserModel | None


class IngestResult(BaseModel):
    user_model: UserModel
    user_model_updated: bool


class InputMessage(TypedDict):
    role: MessageRole
    text: str


class ProviderSettings(BaseModel):
    provider: Literal["openrouter"] = OPENROUTER_PROVIDER
    model: str
    api_key: str
    base_url: str = OPENROUTER_BASE_URL
    timeout_seconds: float = 60.0
    app_name: str | None = APP_NAME
    referer: str | None = None
