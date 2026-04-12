from __future__ import annotations


class EmbeddingError(RuntimeError):
    """Raised when the embedding model call fails."""


class VectorStoreError(RuntimeError):
    """Raised when a vector store operation fails."""
