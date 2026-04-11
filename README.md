## Seahorse

Seahorse is a single-user memory service for agent systems. It gives an agent a small long-term memory layer for user profile facts, session ingest, and past-context recall over MCP or HTTP.

## What It Does

Seahorse is meant to sit beside an agent runtime and handle memory-specific work that you do not want scattered across the agent loop itself.

Core capabilities:

- Persist stable user facts, preferences, and constraints into a structured user profile
- Search previously ingested memory when the agent needs recalled context
- Expose the same memory functions through either MCP tools or plain HTTP endpoints
- Optionally index session transcripts into Qdrant for vector-backed memory search

Current scope:

- Single-user only
- Structured JSON profile storage on disk
- Optional vector memory for session transcript recall
- HTTP adapter and MCP adapter

Not in scope for the MVP:

- Multi-user tenancy
- Embeddings-only architecture without structured profile memory
- LangChain-style orchestration layers across the whole app

## Main Interfaces

Seahorse provides two ways to integrate memory into an agent stack.

### HTTP API

Run with:

```bash
make run
```

The HTTP server listens on `127.0.0.1:8081`.

Endpoints:

- `GET /health`: returns service health, including vector-memory health when enabled
- `GET /user/profile`: returns the current structured user profile
- `GET /memory/search?query=...`: searches recalled memory for a short natural-language query
- `POST /memory/sessions`: ingests a conversation turn or message list and updates long-term memory

Minimal ingest example:

```json
{
  "session_id": "session-123",
  "messages": [
    {"role": "user", "text": "I live in Hangzhou and prefer TypeScript."},
    {"role": "assistant", "text": "Understood."}
  ]
}
```

### MCP Tools

Run with:

```bash
make run-mcp
```

The MCP server runs over stdio and registers these tools:

- `get_user_profile`: returns stable known facts about the user such as background, preferences, and constraints
- `search_memory`: searches past memory for relevant recalled context from a short natural-language query
- `ingest_turn`: persists durable facts learned from a conversation turn into long-term memory

`mcp.enabled_tools` can restrict which of these tools are exposed for a given runtime.

## Configuration

Seahorse reads configuration from two places:

- `config.yaml` for non-secret runtime settings
- environment variables for secrets

Copy [`config.yaml.example`](/Users/david/codes/agent/seahorse/config.yaml.example) to `config.yaml` and adjust the values you need.

Required environment variables:

- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY` only when `vector_memory.enabled: true` and `embedding.api_key_env: OPENAI_API_KEY`

Startup is fail-fast. Seahorse exits during bootstrap if required settings, secrets, or prompt files are missing or invalid.

### Config Modules

#### `provider`

Controls the LLM used for user-profile extraction.

- `name`: provider name, currently `openrouter`
- `model`: extraction model name
- `timeout_seconds`: request timeout for the provider

#### `logger`

Controls runtime logging.

- `log_dir`: directory for log files
- `log_level`: one of `debug`, `info`, `warning`, `error`

#### `storage`

Controls on-disk persisted memory.

- `data_dir`: required storage directory, resolved relative to the project root when not absolute

Structured user profile data is persisted at `storage.data_dir/user_model.json`.

#### `mcp`

Controls MCP tool registration.

- `enabled_tools`: optional allowlist of exposed tools

Supported tool names:

- `get_user_profile`
- `search_memory`
- `ingest_turn`

#### `memory_search`

Controls generic recall behavior.

- `top_k`: how many recalled results `search_memory` returns

#### `vector_memory`

Controls optional transcript vector indexing.

- `enabled`: enables Qdrant-backed vector memory
- `top_k`: how many vector hits are returned during vector-backed recall

When disabled, Seahorse still keeps the structured user profile memory and skips transcript vector indexing.

#### `embedding`

Controls the embedding model used for vector memory.

Required only when `vector_memory.enabled` is `true`.

- `provider`: embedding provider, currently `openai_compatible`
- `model`: embedding model name
- `base_url`: embedding API base URL
- `api_key_env`: environment variable name that stores the embedding API key
- `timeout_seconds`: embedding request timeout

#### `qdrant`

Controls the vector store connection.

Required only when `vector_memory.enabled` is `true`.

- `url`: Qdrant server URL
- `collection_name`: Qdrant collection name

## Quick Start

Install dependencies:

```bash
make sync
```

Run tests:

```bash
make test
```

Start HTTP:

```bash
make run
```

Start MCP:

```bash
make run-mcp
```

You can also run the packaged entrypoints directly:

- `uv run seahorse-http`
- `uv run seahorse-mcp`

## Project Layout

The codebase is organized by layer:

- `src/seahorse/domain`: core models and repository or service interfaces
- `src/seahorse/application`: orchestration and merge logic
- `src/seahorse/infrastructure`: config loading, repositories, providers, extractors, vector integrations
- `src/seahorse/api`: HTTP and MCP transport adapters
- `src/seahorse/prompts`: prompt templates used by extraction flows
- `tests`: wiring, regression, and adapter tests

## Notes

- Seahorse is designed as a focused memory component, not a full agent framework.
- Structured profile memory and vector memory are complementary here: profile memory stores durable facts, while vector memory helps recall prior session context.
- For tool wording guidance and memory-tool design notes, see [docs/tool-design.md](/Users/david/codes/agent/seahorse/docs/tool-design.md) and [docs/session-vector-memory-design.md](/Users/david/codes/agent/seahorse/docs/session-vector-memory-design.md).
