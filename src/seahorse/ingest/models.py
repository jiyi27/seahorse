from __future__ import annotations

from pydantic import BaseModel, Field

from seahorse.domain.models import Message


class ConversationBlock(BaseModel):
    messages: list[Message] = Field(default_factory=list)


class VectorChunk(BaseModel):
    record_id: str
    text_for_embedding: str
    payload: dict[str, object]
