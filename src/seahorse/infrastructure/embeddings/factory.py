from __future__ import annotations

import threading
from collections.abc import Sequence
from typing import Any

import httpx

from seahorse.infrastructure.embeddings.base import (
    EmbeddingModel,
    EmbeddingSettings,
    OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
)
from seahorse.infrastructure.exceptions import EmbeddingError


class OpenAICompatibleEmbeddingModel:
    def __init__(
        self,
        settings: EmbeddingSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._client = http_client or self._build_client()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        url = f"{self._settings.base_url.rstrip('/')}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"
        try:
            response = self._get_client().post(
                url,
                headers=headers,
                json={
                    "model": self._settings.model,
                    "input": texts,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EmbeddingError(
                "Embedding request failed: "
                f"provider={self._settings.provider} "
                f"model={self._settings.model} "
                f"base_url={self._settings.base_url} "
                f"status={exc.response.status_code} "
                f"input_count={len(texts)}"
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError(
                "Embedding request error: "
                f"provider={self._settings.provider} "
                f"model={self._settings.model} "
                f"base_url={self._settings.base_url} "
                f"input_count={len(texts)}"
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise EmbeddingError(
                "Embedding response was not valid JSON: "
                f"provider={self._settings.provider} "
                f"model={self._settings.model}"
            ) from exc

        return self._parse_embeddings(body, expected_count=len(texts))

    def check_connection(self) -> None:
        self.embed_documents(["healthcheck"])

    def _get_client(self):
        return self._client

    def _build_client(self):
        return httpx.Client(
            timeout=self._settings.timeout_seconds,
        )

    def _parse_embeddings(
        self,
        body: dict[str, Any],
        *,
        expected_count: int,
    ) -> list[list[float]]:
        data = body.get("data")
        if not isinstance(data, list):
            raise EmbeddingError(
                "Embedding response did not include a data list: "
                f"provider={self._settings.provider} "
                f"model={self._settings.model}"
            )

        indexed_embeddings: list[tuple[int, list[float]]] = []
        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingError(
                    "Embedding response item was not an object: "
                    f"provider={self._settings.provider} "
                    f"model={self._settings.model}"
                )

            index = item.get("index")
            embedding = item.get("embedding")
            if not isinstance(index, int) or not self._is_number_list(embedding):
                raise EmbeddingError(
                    "Embedding response item had an invalid shape: "
                    f"provider={self._settings.provider} "
                    f"model={self._settings.model}"
                )

            indexed_embeddings.append((index, [float(value) for value in embedding]))

        indexed_embeddings.sort(key=lambda item: item[0])
        embeddings = [embedding for _, embedding in indexed_embeddings]
        if len(embeddings) != expected_count:
            raise EmbeddingError(
                "Embedding response count did not match input count: "
                f"provider={self._settings.provider} "
                f"model={self._settings.model} "
                f"expected={expected_count} "
                f"actual={len(embeddings)}"
            )
        return embeddings

    def _is_number_list(self, value: Any) -> bool:
        return (
            isinstance(value, Sequence)
            and not isinstance(value, str | bytes)
            and all(isinstance(item, int | float) for item in value)
        )


_EMBEDDING_CACHE: dict[EmbeddingSettings, OpenAICompatibleEmbeddingModel] = {}
_LOCK = threading.Lock()


def build_embedding_model(settings: EmbeddingSettings) -> EmbeddingModel:
    if settings.provider != OPENAI_COMPATIBLE_EMBEDDING_PROVIDER:
        raise RuntimeError(f"Unsupported embedding provider: {settings.provider}")

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
