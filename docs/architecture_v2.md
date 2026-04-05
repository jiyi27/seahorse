# Seahorse Architecture V2

## Overview

Seahorse is a single-user memory service exposed through MCP tools and an HTTP API.

The MVP has one concrete goal:

1. Accept turn content or session transcripts.
2. Use an LLM to extract updates for a single user profile.
3. Persist `CoreRule` and `UserModel` as Markdown documents.

The MVP does not persist episodes as first-class records.
Episode ingestion exists only as an input path for user-model extraction.

Future semantic episode indexing, vector storage, and workflow orchestration are explicitly separate from the MVP write path.

---

## Design Constraints

1. Single-user only.
   Seahorse serves exactly one user profile. There is no multi-user routing, tenancy, or `user_id` in the MVP domain model.

2. `CoreRule` is one Markdown document.
   It represents the stable operating rule or personality baseline for the agent.

3. `UserModel` is one Markdown document.
   It represents the current accumulated understanding of the user.

4. User-model extraction uses an LLM.
   Provider integration must be isolated from application logic so it can be replaced or tested independently.

5. Storage and extraction must stay decoupled.
   API handlers should not know prompt details.
   Extractors should not know file layout details.
   Repositories should not know which API surface invoked them.

---

## Non-Goals for MVP

The following are intentionally out of scope for the first version:

1. Multi-user support.
2. Episode persistence as Markdown or any other durable store.
3. Qdrant integration.
4. Embedding generation and semantic recall.
5. LangChain or LangGraph workflow orchestration.
6. Background job systems and async pipelines.

These may be added later behind dedicated interfaces.

---

## Architecture Principles

### 1. Separate input adapters from business logic

MCP and HTTP are transport adapters only.
They validate input, normalize it, and call application services.

### 2. Separate business orchestration from provider calls

Application services coordinate the workflow.
LLM-specific prompting and completion calls live behind extractor and provider interfaces.

### 3. Separate persistence by document type

`CoreRule` and `UserModel` are stored as dedicated Markdown documents.
They should not be hidden behind an over-generalized storage backend.

### 4. Keep future episode indexing as an optional hook

The application layer may call an episode pipeline hook, but the MVP implementation is a no-op.
This keeps the current flow stable while leaving a clean extension point for future vector storage.

---

## Recommended Project Structure

```text
seahorse/
├── src/
│   └── seahorse/
│       ├── __init__.py
│       ├── api/
│       │   ├── mcp_server.py
│       │   └── http_server.py
│       ├── application/
│       │   ├── ingest_service.py
│       │   ├── recall_service.py
│       │   └── user_model_merger.py
│       ├── domain/
│       │   ├── models.py
│       │   ├── repositories.py
│       │   └── services.py
│       ├── infrastructure/
│       │   ├── config.py
│       │   ├── extractors/
│       │   │   └── llm_user_model_extractor.py
│       │   ├── providers/
│       │   │   ├── base.py
│       │   │   └── openai_provider.py
│       │   ├── repositories/
│       │   │   ├── core_rule_markdown.py
│       │   │   └── user_model_markdown.py
│       │   └── episodes/
│       │       └── noop_episode_pipeline.py
│       ├── prompts/
│       │   └── user_model_extraction.md
│       └── tools/
│           ├── ingest_turn.py
│           └── recall_context.py
├── data/
│   ├── core_rule.md
│   └── user_model.md
├── tests/
│   ├── test_repositories.py
│   ├── test_services.py
│   ├── test_tools.py
│   └── test_http_api.py
├── docs/
│   ├── architecture.md
│   └── architecture_v2.md
├── pyproject.toml
└── .gitignore
```

---

## Domain Model

The MVP domain model should stay small and stable.

### `CoreRule`

Represents the single active system-level memory document.

Suggested fields:

```python
class CoreRule(BaseModel):
    content: str
    updated_at: datetime
```

### `UserModel`

Represents the single active user profile document.

Suggested fields:

```python
class UserModel(BaseModel):
    content: str
    updated_at: datetime
    version: int
```

### `ConversationInput`

Represents incoming data to be processed.
It is an application input model, not a persisted entity.

Suggested fields:

```python
class ConversationInput(BaseModel):
    source: Literal["mcp", "http"]
    content: str | None = None
    messages: list[Message] = []
    session_id: str | None = None
```

### `UserModelPatch`

Represents the structured extraction result returned by the LLM extractor.
The extractor should not directly rewrite the Markdown file.

Suggested fields:

```python
class UserModelPatch(BaseModel):
    summary: str
    facts_to_add: list[str] = []
    preferences_to_add: list[str] = []
    constraints_to_add: list[str] = []
    stale_items_to_remove: list[str] = []
```

This model is important for decoupling.
It keeps extraction logic, merge logic, and persistence logic separate.

---

## Repository Interfaces

Do not introduce a global `StorageBackend` abstraction for the MVP.
It creates the wrong coupling because `CoreRule`, `UserModel`, and future episode indexing have different storage behavior.

Use narrow interfaces instead.

```python
class CoreRuleRepository(Protocol):
    def load(self) -> CoreRule: ...


class UserModelRepository(Protocol):
    def load(self) -> UserModel | None: ...
    def save(self, model: UserModel) -> None: ...
```

These interfaces are intentionally small.
They are easy to fake in tests and easy to replace later.

---

## Provider Layer

The system will rely on an LLM for user-model extraction, so provider abstraction is part of the MVP design.

### Provider interface

```python
class LLMProvider(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...
```

This interface should stay minimal in the first version.
Do not prematurely model tools, streaming, retries, or agent workflows unless the MVP already requires them.

### Why this layer exists

1. It isolates vendor SDK details.
2. It makes extractor testing easy.
3. It avoids leaking OpenAI-specific request objects into application code.
4. It leaves room for future provider swaps without rewriting service logic.

---

## Extractor Layer

The extractor converts raw conversation input into a structured `UserModelPatch`.

### Extractor interface

```python
class UserModelExtractor(Protocol):
    def extract(
        self,
        conversation: ConversationInput,
        current_user_model: UserModel | None,
        core_rule: CoreRule,
    ) -> UserModelPatch: ...
```

### Responsibilities

The extractor is responsible for:

1. Prompt assembly.
2. Calling the provider.
3. Parsing model output into `UserModelPatch`.

The extractor is not responsible for:

1. Reading or writing Markdown files.
2. Handling MCP or HTTP protocols.
3. Deciding where future episode data is stored.

This boundary is one of the most important parts of the design.

---

## Application Services

Application services own the business workflow.
They are the only place where repositories, extractors, and future hooks come together.

### `IngestService`

This is the main write path shared by MCP and HTTP.

Flow:

```text
input adapter
-> build ConversationInput
-> load CoreRule
-> load current UserModel
-> extractor.extract(...)
-> merge patch into current model
-> save UserModel
-> call optional episode pipeline hook
-> return result
```

Suggested responsibilities:

1. Coordinate the ingest workflow.
2. Keep write behavior consistent across MCP and HTTP.
3. Invoke the future episode pipeline through an interface only.

### `RecallService`

This is the main read path.

Flow:

```text
load CoreRule
load UserModel
return both as recall context
```

In the MVP, recall does not query episode history.

---

## Merge Strategy

Do not let the extractor overwrite `user_model.md` directly.

Introduce a dedicated merger:

```python
class UserModelMerger:
    def merge(
        self,
        current: UserModel | None,
        patch: UserModelPatch,
    ) -> UserModel: ...
```

Why this matters:

1. Merge policy changes are common.
2. Prompt changes should not force repository changes.
3. The merger can be tested without any provider dependency.

For the MVP, the merger can be simple:

1. Convert the previous Markdown into sections.
2. Append or update extracted facts.
3. Rebuild the final Markdown document deterministically.

Deterministic output is useful for diffing and test stability.

---

## API Layer

### MCP tools

Recommended tool names:

1. `recall_context`
2. `ingest_turn`

These names better match the MVP behavior than `commit_episode`.

### HTTP endpoints

Recommended endpoint:

```text
POST /memory/ingest
```

Suggested request shape:

```json
{
  "session_id": "optional-session-id",
  "content": "optional-plain-text-summary",
  "messages": [
    {"role": "user", "text": "..."},
    {"role": "assistant", "text": "..."}
  ]
}
```

This endpoint means "process this input for memory updates".
It does not promise session persistence.

---

## Data Layout

For the MVP, keep storage explicit and simple:

```text
data/
  core_rule.md
  user_model.md
```

This matches your requirement:

1. One `CoreRule` document.
2. One `UserModel` document.
3. No episode persistence in the first version.

---

## Future Episode Pipeline

Episode processing should be modeled as an optional interface from day one, but implemented as a no-op in the MVP.

### Interface

```python
class EpisodePipeline(Protocol):
    def process(self, conversation: ConversationInput) -> None: ...
```

### MVP implementation

```python
class NoopEpisodePipeline:
    def process(self, conversation: ConversationInput) -> None:
        return None
```

### Future implementation

The future implementation may include:

1. transcript normalization
2. chunking
3. summarization
4. embedding
5. vector upsert to Qdrant
6. semantic retrieval

This is where LangChain or LangGraph can appear later if they are actually useful.

They should remain internal to the episode pipeline implementation and should not leak into the rest of the system.

---

## Dependency Direction

The dependency direction should be strict:

```text
api/tools
  -> application
  -> domain

infrastructure
  -> domain

application
  -> domain
  -> infrastructure interfaces only through constructor injection
```

Practical rule:

1. `api` imports `application`.
2. `application` imports `domain`.
3. concrete infrastructure is wired at startup.
4. domain imports nothing from infrastructure.

This keeps the system testable and prevents framework details from spreading.

---

## Testing Strategy

Testing should follow the same separation.

### Repository tests

Test Markdown repository behavior directly:

1. load existing file
2. initialize missing file behavior
3. save updated document

### Merger tests

Test pure merge logic without I/O or LLM calls:

1. merge into empty model
2. merge incremental facts
3. remove stale facts
4. verify deterministic Markdown output

### Service tests

Test `IngestService` and `RecallService` with fakes:

1. fake repositories
2. fake extractor
3. fake episode pipeline

This is where most business behavior should be validated.

### API tests

Keep API tests thin:

1. request validation
2. adapter to service wiring
3. response schema

Do not rely on API tests to verify merge logic or provider behavior.

---

## MVP Implementation Plan

### Phase 1: Stable domain and boundaries

Implement:

1. `domain/models.py`
2. `domain/repositories.py`
3. `domain/services.py`
4. `application/user_model_merger.py`

Goal:
Lock the core abstractions before writing adapters.

### Phase 2: Markdown persistence

Implement:

1. `core_rule_markdown.py`
2. `user_model_markdown.py`
3. `data/core_rule.md`
4. `data/user_model.md` initialization behavior

Goal:
Make the document layer concrete and testable.

### Phase 3: Provider and extractor

Implement:

1. `providers/base.py`
2. one concrete provider implementation
3. `llm_user_model_extractor.py`
4. prompt template under `prompts/`

Goal:
Keep all model-specific behavior behind one boundary.

### Phase 4: Application services

Implement:

1. `IngestService`
2. `RecallService`
3. `NoopEpisodePipeline`

Goal:
Establish one shared write path and one shared read path.

### Phase 5: API adapters

Implement:

1. MCP tool adapters
2. HTTP route adapter

Goal:
Expose the same application services through different transports without duplicating business logic.

### Phase 6: Future episode indexing

Later only.

Possible additions:

1. chunking pipeline
2. embedding provider
3. Qdrant-backed episode index
4. optional workflow orchestration

This phase should not require a redesign of the MVP layers.

---

## Final Recommendation

Compared with the previous draft, the plan changes in three important ways:

1. Remove multi-user assumptions entirely.
2. Remove episode persistence from the MVP.
3. Replace the generic storage abstraction with narrower document repositories plus a separate future episode pipeline hook.

This design is a better fit for your actual product direction:

1. single-user memory
2. one `CoreRule` Markdown document
3. one `UserModel` Markdown document
4. LLM-based profile extraction
5. future vector episode processing without contaminating the MVP

If this document is accepted, the next step should be implementing the Phase 1 skeleton only, not the full future plan.
