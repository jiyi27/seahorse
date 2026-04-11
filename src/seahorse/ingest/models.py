from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from seahorse.domain.models import Message
from seahorse.ingest.constants import CHUNK_VERSION


class ConversationBlock(BaseModel):
    session_id: str | None = None
    start_message_index: int
    end_message_index: int
    messages: list[Message] = Field(default_factory=list)


class ConversationChunk(BaseModel):
    chunk_id: str
    chunk_index: int
    session_id: str | None = None
    start_message_index: int
    end_message_index: int
    messages: list[Message] = Field(default_factory=list)
    chunk_version: str = CHUNK_VERSION


class PreparedConversationChunk(BaseModel):
    chunk: ConversationChunk
    text_for_embedding: str
    payload: dict[str, Any]


class PreparedVectorRecord(BaseModel):
    record_id: str
    text_for_embedding: str
    payload: dict[str, Any]
