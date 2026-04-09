from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingSettings:
    provider: str
    model: str
    base_url: str
    api_key: str
    timeout_seconds: float


class OpenAICompatibleEmbeddingModel:
    def __init__(self, settings: EmbeddingSettings) -> None:
        self._settings = settings
        self._client = self._build_client()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._get_client().embed_documents(texts)

    def check_connection(self) -> None:
        self.embed_documents(["healthcheck"])

    def _get_client(self):
        return self._client

    def _build_client(self):
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise RuntimeError(
                "langchain-openai is required for vector memory embeddings"
            ) from exc

        return OpenAIEmbeddings(
            base_url=self._settings.base_url,
            api_key=self._settings.api_key,
            model=self._settings.model,
            request_timeout=self._settings.timeout_seconds,
            check_embedding_ctx_length=False,
            tiktoken_enabled=False,
        )


_EMBEDDING_CACHE: dict[EmbeddingSettings, OpenAICompatibleEmbeddingModel] = {}
_LOCK = threading.Lock()


def build_embedding_model(settings: EmbeddingSettings) -> OpenAICompatibleEmbeddingModel:
    cached = _EMBEDDING_CACHE.get(settings)
    if cached is not None:
        return cached

    with _LOCK:
        cached = _EMBEDDING_CACHE.get(settings)
        if cached is not None:
            return cached

        instance = OpenAICompatibleEmbeddingModel(settings)
        _EMBEDDING_CACHE[settings] = instance
        return instance
