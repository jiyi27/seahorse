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
- the environment variable named by `vector_memory.embedding.api_key_env` when that field is set

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

#### `vector_memory`

Controls optional transcript vector indexing.

- `enabled`: enables Qdrant-backed vector memory
- `retrieval`: vector search result sizing
- `embedding`: embedding-model settings
- `store`: vector-store settings

When disabled, Seahorse still keeps the structured user profile memory and skips transcript vector indexing.
If your embedding endpoint does not require authentication, such as a local Ollama OpenAI-compatible endpoint, leave `api_key_env` unset.

`vector_memory.retrieval` fields:

- `max_chunks`: how many chunks are fetched from the vector store for one search
- `max_blocks`: how many conversation blocks are returned after chunk deduplication

`vector_memory.embedding` fields:

- `provider`: embedding provider, currently `openai_compatible`
- `model`: embedding model name
- `base_url`: embedding API base URL such as `https://api.openai.com/v1` or `http://localhost:11434/v1`
- `api_key_env`: optional environment variable name for the embedding API key
- `timeout_seconds`: embedding request timeout

`vector_memory.store` fields:

- `url`: Qdrant server URL
- `collection_name`: Qdrant collection name

## Quick Start

### 1. Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/) if you want local Qdrant and Ollama
- [uv](https://github.com/astral-sh/uv) for Python dependency management

### 2. Start Local Infrastructure

Seahorse can use local Qdrant and Ollama in the same way as your `DocMind` setup.

First-time setup:

```bash
make infra-init
```

This will:

- start `qdrant` on `http://localhost:6333`
- start `ollama` on `http://localhost:11434`
- pull `nomic-embed-text:latest` into the Ollama container
- sync Python dependencies

Subsequent runs are handled automatically by `make run`, which starts infrastructure before the server.

Stop local infrastructure:

```bash
make infra-down
```

If you need to pull the embedding model again:

```bash
make ollama-pull
```

You can also run project-scoped container commands directly:

```bash
docker compose exec <service> <command>
```

### 3. Configure Seahorse

Install dependencies manually if you are not using `make infra-init`:

```bash
make sync
```

Copy [`config.yaml.example`](/Users/david/codes/agent/seahorse/config.yaml.example) to `config.yaml` and adjust the values you need.

For local Ollama + Qdrant vector memory, a typical config looks like:

```yaml
vector_memory:
  enabled: true
  retrieval:
    max_chunks: 10
    max_blocks: 5
  embedding:
    provider: openai_compatible
    model: nomic-embed-text:latest
    base_url: http://localhost:11434/v1
    timeout_seconds: 30.0
  store:
    url: http://localhost:6333
    collection_name: seahorse_memory
```

Required environment variables:

- `OPENROUTER_API_KEY`
- `vector_memory.embedding.api_key_env` only when your embedding endpoint requires authentication

For local Ollama, no embedding API key is required. A minimal local setup can use:

```bash
export OPENROUTER_API_KEY=...
```

### 4. Run and Verify

Run tests:

```bash
make test
```

Start HTTP (also starts Qdrant and Ollama if not already running):

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

The HTTP server listens on `127.0.0.1:8081`.
If vector memory is enabled, `GET /health` will also report embedding and Qdrant health.

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
