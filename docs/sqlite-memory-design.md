# SQLite Memory: Design

An alternative to the Qdrant vector pipeline. The two implementations are mutually exclusive — the goal is to run both and compare retrieval quality, then drop the weaker one.

## Motivation

Vector search (Qdrant) requires an embedding model and a running Qdrant instance. SQLite + FTS5 requires neither. The trade-off is semantic search vs. keyword search, but for structured conversation recall at single-user scale (~1M rows) SQLite FTS5 is worth evaluating.

## Database Schema

```sql
-- One row per indexable message (user or assistant only)
CREATE TABLE conversation_chunks (
    id            TEXT    PRIMARY KEY,   -- child_chunk_id (deterministic UUID, reused from ingest)
    block_id      TEXT    NOT NULL,      -- parent_block_id (for dedup at retrieval time)
    session_id    TEXT,                  -- from ConversationInput.session_id (nullable)
    turn_index    INTEGER NOT NULL,      -- which block within this ingest batch (0-based)
    chunk_index   INTEGER NOT NULL,      -- position within the block (0-based)
    role          TEXT    NOT NULL,      -- 'user' | 'assistant'
    message_text  TEXT    NOT NULL,      -- single message text (the search target)
    block_content TEXT    NOT NULL,      -- full block text including tool messages (returned on hit)
    ingested_at   TEXT    NOT NULL       -- ISO8601 timestamp
);

CREATE INDEX idx_chunks_session  ON conversation_chunks(session_id);
CREATE INDEX idx_chunks_block_id ON conversation_chunks(block_id);

-- FTS5 full-text index over message_text
CREATE VIRTUAL TABLE conversation_chunks_fts USING fts5(
    message_text,
    content='conversation_chunks',
    content_rowid='rowid'
);
```

**Field notes:**

- `block_id` and `block_content` mirror the `parent_block_id` and `content` fields in the Qdrant payload. Retrieval dedup logic is identical.
- `turn_index` is the block's position in the list returned by `build_conversation_blocks()`. Together with `session_id` it identifies a specific conversation turn.
- `block_content` is stored redundantly in every chunk that belongs to the same block (same as the vector approach). This avoids a JOIN at retrieval time.
- `id` is the existing `child_chunk_id` (deterministic hash), so re-ingesting the same conversation is idempotent via `INSERT OR REPLACE`.

## Search

FTS5 replaces vector similarity. The query flow mirrors the vector path:

```sql
SELECT c.block_id, c.block_content
FROM conversation_chunks c
JOIN conversation_chunks_fts fts ON c.rowid = fts.rowid
WHERE conversation_chunks_fts MATCH ?
ORDER BY rank
LIMIT :max_chunks;
```

Results are then deduplicated by `block_id` and capped at `max_blocks` — same post-processing as the vector path (`conversation_recall.py`).

## New Files

```
src/seahorse/infrastructure/
  sqlitestore/
    __init__.py
    sqlite_store.py                         # schema init, upsert, fts search

  pipelines/
    sqlite_conversation_pipeline.py         # implements ConversationVectorPipeline

src/seahorse/application/
  sqlite_conversation_search_service.py     # implements the MemorySearchService interface
```

## Config

New section in `config.yaml`, parallel to `vector_memory`:

```yaml
sqlite_memory:
  enabled: true
  db_path: "storage/conversation.db"
  retrieval:
    max_chunks: 10
    max_blocks: 5
```

`vector_memory.enabled` and `sqlite_memory.enabled` are mutually exclusive. Bootstrap selects the active path at startup.

## What Is Reused Unchanged

| Component | Reused as-is |
|---|---|
| `build_conversation_blocks()` | Block splitting logic, unchanged |
| `build_child_chunks()` | Produces `PreparedVectorRecord`; `id` and payload fields map directly to SQLite columns |
| `build_parent_block_id()` / `build_child_chunk_id()` | Deterministic IDs, idempotent re-ingest |
| `conversation_recall.py` | Dedup and result assembly logic, unchanged |
| `MemorySearchResultItem` | Output format, unchanged |

The SQLite pipeline replaces only the final step of the ingest path (embed + upsert to Qdrant → `INSERT OR REPLACE` into SQLite) and the query step (Qdrant similarity search → FTS5 MATCH).
