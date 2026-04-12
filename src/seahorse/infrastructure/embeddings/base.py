from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

OPENAI_COMPATIBLE_EMBEDDING_PROVIDER = "openai_compatible"
SUPPORTED_EMBEDDING_PROVIDERS = frozenset({OPENAI_COMPATIBLE_EMBEDDING_PROVIDER})


class EmbeddingModel(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def check_connection(self) -> None: ...


@dataclass(frozen=True)
class EmbeddingSettings:
    provider: str
    model: str
    base_url: str
    api_key: str
    timeout_seconds: float
