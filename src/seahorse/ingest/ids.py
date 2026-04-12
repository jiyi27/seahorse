from __future__ import annotations

import uuid
from hashlib import sha1


_CHUNK_NAMESPACE = uuid.UUID("b1a2e3d4-f5c6-7890-abcd-ef1234567890")


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
    key = f"{parent_block_id}\n{child_index}\n{normalized_text}"
    return str(uuid.uuid5(_CHUNK_NAMESPACE, key))
