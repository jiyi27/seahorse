from __future__ import annotations

import httpx
import pytest

from seahorse.infrastructure.config import AppConfig, load_app_config_from_yaml
from seahorse.infrastructure.embeddings.base import (
    EmbeddingSettings,
    OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
)
from seahorse.infrastructure.embeddings.factory import (
    OpenAICompatibleEmbeddingModel,
    build_embedding_model,
)
from seahorse.infrastructure.exceptions import EmbeddingError


def test_app_config_rejects_unsupported_embedding_provider() -> None:
    with pytest.raises(Exception, match="vector_memory.embedding.provider"):
        AppConfig.model_validate(
            {
                "storage": {"data_dir": "data"},
                "vector_memory": {"embedding": {"provider": "ollama_native"}},
            }
        )


def test_load_app_config_from_yaml_rejects_unsupported_embedding_provider(
    tmp_path,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        (
            "storage:\n"
            "  data_dir: data\n"
            "vector_memory:\n"
            "  embedding:\n"
            "    provider: ollama_native\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="vector_memory.embedding.provider"):
        load_app_config_from_yaml(config_path)


def test_build_embedding_model_returns_openai_compatible_model() -> None:
    model = build_embedding_model(
        EmbeddingSettings(
            provider=OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
            model="text-embedding-3-small",
            base_url="https://example.com/v1",
            api_key="test-key",
            timeout_seconds=30.0,
        )
    )

    assert isinstance(model, OpenAICompatibleEmbeddingModel)


def test_openai_compatible_embedding_model_posts_to_embeddings_endpoint() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    model = OpenAICompatibleEmbeddingModel(
        EmbeddingSettings(
            provider=OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
            model="nomic-embed-text:latest",
            base_url="http://localhost:11434/v1/",
            api_key="ollama",
            timeout_seconds=5.0,
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = model.embed_documents(["first", "second"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert captured_request is not None
    assert str(captured_request.url) == "http://localhost:11434/v1/embeddings"
    assert captured_request.headers["Authorization"] == "Bearer ollama"


def test_openai_compatible_embedding_model_omits_auth_header_when_api_key_missing() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]})

    model = OpenAICompatibleEmbeddingModel(
        EmbeddingSettings(
            provider=OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
            model="nomic-embed-text",
            base_url="http://localhost:11434/v1",
            api_key=None,
            timeout_seconds=5.0,
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = model.embed_documents(["hello"])

    assert result == [[0.1, 0.2]]
    assert captured_request is not None
    assert "Authorization" not in captured_request.headers


def test_openai_compatible_embedding_model_wraps_http_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    model = OpenAICompatibleEmbeddingModel(
        EmbeddingSettings(
            provider=OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
            model="text-embedding-3-small",
            base_url="https://example.com/v1",
            api_key="test-key",
            timeout_seconds=5.0,
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(EmbeddingError, match="status=503"):
        model.embed_documents(["hello"])


def test_openai_compatible_embedding_model_rejects_invalid_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "vector": [0.1, 0.2]}]})

    model = OpenAICompatibleEmbeddingModel(
        EmbeddingSettings(
            provider=OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
            model="text-embedding-3-small",
            base_url="https://example.com/v1",
            api_key="test-key",
            timeout_seconds=5.0,
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(EmbeddingError, match="invalid shape"):
        model.embed_documents(["hello"])
