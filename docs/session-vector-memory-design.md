# Session Vector Memory Design

## Goal

Seahorse already accepts full session transcripts through `POST /memory/sessions`.

That ingest path now has two fixed responsibilities:

1. Update the stable user profile.
2. Convert the session transcript into retrievable vector memory.

This document defines how the second responsibility should be designed so that:

- embedding text stays semantically clean
- raw session data remains recoverable
- chunking strategy can change without rewriting the whole pipeline
- ingest and retrieval logic stay decoupled
- the system can use Qdrant without adopting DocMind's document-oriented architecture

## Core Design Decisions

### 1. Two Different Representations

The vector pipeline should produce two different representations of the same chunk:

- `text_for_embedding`
  - used only for embeddings and vector search
  - should mainly contain `user` and `assistant` dialogue text
- `payload`
  - stored in Qdrant payload metadata
  - should preserve the original structured content needed for reconstruction

Reason:

- tool output is often noisy and weakens semantic embeddings
- raw tool data is still useful for replay, inspection, and accurate recall
- embedding text and stored payload should not be coupled

### 2. Chunk Boundary Logic Must Be Independent

The logic that decides chunk boundaries must be isolated from:

- embedding text generation
- payload construction
- vector DB writing

Reason:

- chunk policy will likely change over time
- changing chunk size or merge rules should not force changes in storage logic
- duplicate chunking bugs become easier to control when boundary selection is centralized

### 3. Tool Data Should Influence Payload, Not Embedding Text

Default rule:

- `user` and `assistant` text participate in embedding text
- `tool_calls` and `tool_results` do not participate in embedding text by default
- tool information is preserved inside payload

This keeps vector semantics focused on the actual conversation while preserving the full original record.

### 4. Session Ingest Orchestrates; Pipelines Own Their Own Logic

`SessionIngestService` should remain a coordinator only.

It should not know:

- how chunking works
- how text is cleaned
- how embeddings are generated
- how Qdrant payloads are shaped

Those details belong inside the conversation vector pipeline and its helpers.

## Current Request Shape

The current `/memory/sessions` request body already carries a full session transcript, including fields such as:

- `role`
- `text`
- `tool_calls`
- `tool_results`
- `compact_summary`
- `metadata`
- `is_interrupted_turn`

This means Seahorse is not ingesting isolated messages. It is ingesting a structured session event stream.

The vector pipeline should therefore treat the input as a session transcript first, and only later derive embedding chunks from it.

## Recommended Chunking Model

### Step 1. Build Conversation Blocks

First convert the raw message list into `conversation blocks`.

Default rule:

- a block starts at a `user` message
- a block includes the related assistant replies until the next `user` message
- tool data stays attached to that block as structured payload context

This gives stable semantic units such as:

- user asks something
- assistant responds
- optional tool interaction happens
- assistant finalizes response

### Step 2. Apply Chunk Policy

Then apply chunk policy to the blocks.

Default first version:

- one conversation block becomes one chunk
- very short adjacent blocks may be merged
- very large blocks may be split again

Important:

- the pipeline should never chunk directly from raw messages in multiple places
- all chunking should go through one dedicated chunk policy module

## What Goes Into Embedding Text

Default `text_for_embedding` should include:

- normalized user text
- normalized assistant text

Default `text_for_embedding` should exclude:

- raw tool JSON
- raw tool result payloads
- long system prompt text
- transport-specific metadata

Potential format:

```text
[user]
I want have a memory system for it

[assistant]
Nice, that's a core piece for any agent...
```

The exact rendering format can evolve, but the principle should remain:

- optimize for semantic search quality
- do not optimize for perfect replay here

## What Goes Into Payload

Qdrant payload should preserve enough data to reconstruct useful context after retrieval.

Recommended payload fields:

- `session_id`
- `chunk_id`
- `chunk_index`
- `start_message_index`
- `end_message_index`
- `roles_present`
- `user_text`
- `assistant_text`
- `messages`
- `has_tool_calls`
- `tool_names`
- `is_interrupted`
- `created_at`
- `chunk_version`

Recommended rule:

- store original structured messages inside payload
- retrieval returns payload-derived context, not just embedding text

## Preventing Duplicate Chunk Inserts

Duplicate prevention should not rely on ad hoc checks deep in the storage layer.

Instead, each chunk should have a stable deterministic id.

Recommended `chunk_id` inputs:

- `session_id`
- `start_message_index`
- `end_message_index`
- `chunk_version`

Optional:

- hash of normalized embedding text

This allows the vector store layer to use upsert semantics safely.

## Recommended Internal Module Boundaries

For conversation vector ingest:

- `src/seahorse/ingest/`
  - session-ingest-specific orchestration and pure ingest logic
- `src/seahorse/retrieval/`
  - vector search and recall shaping logic

Reason:

- ingest and retrieval will both grow
- they are related, but they solve different problems
- keeping them in one mixed folder will create coupling over time

Recommended ingest-side modules:

- `src/seahorse/ingest/conversation_blocks.py`
  - build conversation blocks from raw messages
- `src/seahorse/ingest/chunk_policy.py`
  - decide how blocks become chunks
- `src/seahorse/ingest/embedding_text.py`
  - generate `text_for_embedding`
- `src/seahorse/ingest/payloads.py`
  - generate Qdrant payloads
- `src/seahorse/ingest/vector_pipeline.py`
  - orchestrate the whole vector ingest flow
- `src/seahorse/ingest/models.py`
  - internal models like `ConversationBlock` and `ConversationChunk`

Recommended retrieval-side modules:

- `src/seahorse/retrieval/vector_search_service.py`
  - query Qdrant
- `src/seahorse/retrieval/result_ranking.py`
  - optional ranking or post-filtering
- `src/seahorse/retrieval/result_rendering.py`
  - convert payloads into memory results returned to callers

This is more future-proof than leaving both concerns under the current broad `application/` or `infrastructure/` buckets without a dedicated home.

## Why Separate `ingest/` and `retrieval/` Folders

This split is recommended once vector memory is introduced.

Reason:

- the current stable-profile flow is small enough for `application/`
- vector memory introduces a second subsystem with enough internal structure to justify its own folders
- ingest and retrieval are natural lifecycle stages
- future work such as reranking, backfill, reindex, and chunk version migrations will fit more cleanly

This does not replace the existing high-level layering.

Instead:

- `api/` remains adapters
- `domain/` remains stable interfaces and core models
- `application/` remains service orchestration
- `infrastructure/` remains provider/storage integrations
- `ingest/` and `retrieval/` become feature modules for vector memory behavior

## Qdrant Integration Guidance

DocMind's Qdrant wrapper is a useful reference in a few specific ways:

- create a thin wrapper over `qdrant-client`
- cache client/store creation where appropriate
- ensure collections exist before use
- probe vector size from the embedding model instead of hardcoding
- use payload metadata for filtering and reconstruction

Those ideas are worth borrowing.

But Seahorse should not copy DocMind's document/knowledge-base structure.

For Seahorse, the Qdrant layer should be shaped around sessions and chunks, not documents and knowledge bases.

Recommended Seahorse vector-store module:

- `src/seahorse/infrastructure/vectorstore/qdrant_store.py`

Recommended responsibilities:

- create `QdrantClient`
- ensure the Seahorse collection exists
- upsert chunk vectors with payload
- search by embedding vector
- optionally delete or replace chunks by `session_id`

Recommended collection naming:

- single-user MVP: one fixed collection, for example `seahorse_memory`

Recommended Qdrant payload keys:

- `session_id`
- `chunk_id`
- `chunk_index`
- `chunk_version`
- `source_type`
- `roles_present`
- `tool_names`
- `payload`

## Config Recommendation

Vector memory should introduce its own config section instead of overloading existing provider config.

Recommended future config sections:

```yaml
vector_memory:
  enabled: true
  collection_name: seahorse_memory
  top_k: 8
  chunk_version: v1

embedding:
  provider: openai
  model: text-embedding-3-small
  timeout_seconds: 30

qdrant:
  url: http://localhost:6333
```

Reason:

- embedding and chat completion are different operational concerns
- vector DB config should not be hidden inside generic provider config
- chunk versioning should be explicit

## Logging Recommendation

The vector pipeline should use the existing request `context_id`.

Recommended events:

- `conversation_vector_pipeline.started`
- `conversation_vector_pipeline.blocks_built`
- `conversation_vector_pipeline.chunks_built`
- `conversation_vector_pipeline.embeddings_created`
- `conversation_vector_pipeline.points_upserted`
- `conversation_vector_pipeline.completed`

Debug-level events may include:

- chunk count
- message index ranges
- chunk ids
- selected tool names

Do not log full vectors.

## Implementation Phases

### Phase 1. Pure Chunking and Modeling

Implement only pure logic:

- internal models
- conversation block builder
- chunk policy
- embedding text builder
- payload builder
- deterministic chunk id generation

No embedding calls yet.
No Qdrant writes yet.

Goal:

- lock in the chunking semantics
- write focused unit tests for chunk boundaries and payload shaping

### Phase 2. Embedding and Qdrant Storage

Implement:

- embedding provider interface
- Qdrant store wrapper
- collection bootstrap
- upsert flow from chunks to vectors

Goal:

- persist searchable conversation memory
- keep all storage concerns behind a thin infrastructure layer

### Phase 3. Retrieval Path

Implement:

- vector search service
- payload-to-memory-result rendering
- optional filters by recency or session

Goal:

- expose retrievable conversation memory cleanly to callers

### Phase 4. Operational Improvements

Optional later work:

- chunk version migrations
- background reindex jobs
- reranking
- dedupe/backfill tooling
- async ingestion if latency becomes too high

## Final Recommendation

The next implementation step should not be Qdrant first.

The next step should be Phase 1:

- define the chunking domain cleanly
- keep chunk boundary selection independent
- keep embedding text generation independent
- keep payload construction independent

Once those boundaries are correct, plugging in embeddings and Qdrant becomes much safer.
