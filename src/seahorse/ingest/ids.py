from __future__ import annotations

from hashlib import sha1


def build_parent_block_id(content: str) -> str:
    normalized_content = content.strip()
    digest = sha1(normalized_content.encode("utf-8")).hexdigest()[:12]
    return f"block:{digest}"


def build_child_chunk_id(
    *,
    parent_block_id: str,
    child_index: int,
    embedding_text: str,
) -> str:
    normalized_text = embedding_text.strip()
    digest = sha1(
        f"{parent_block_id}\n{child_index}\n{normalized_text}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{parent_block_id}:child:{digest}"
