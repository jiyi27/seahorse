## Seahorse

Seahorse is a single-user memory service for agent systems. It gives an agent a small long-term memory layer for user profile facts, session ingest, and past-context recall over MCP or HTTP.

Seahorse is meant to sit beside an agent runtime and handle memory-specific work that you do not want scattered across the agent loop itself.

Core capabilities:

- Persist stable user facts, preferences, and constraints into a structured user profile
- Search previously ingested memory when the agent needs recalled context
- Expose the same memory functions through either MCP tools or plain HTTP endpoints
- Optionally index session transcripts into Qdrant for vector-backed memory search

## Quick Start

### 1. Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/) for local Qdrant
- [uv](https://github.com/astral-sh/uv) for Python dependency management

Export required secrets before starting:

```bash
export OPENROUTER_API_KEY=your-key-here
```

### 2. Copy Example Files

`config.yaml` and `Makefile` are not tracked by git — copy from the provided examples and adjust to your setup:

```bash
cp config.yaml.example config.yaml
cp Makefile.example Makefile
```

### 3. Start Infrastructure and Sync Dependencies

First-time setup (starts Qdrant, syncs Python deps):

```bash
make infra-init
```

Stop local infrastructure:

```bash
make infra-down
```

### 5. Run

Start the HTTP server:

```bash
make run
```

The HTTP server listens on `127.0.0.1:8081`.

## Configuration

### `provider`

Controls the LLM used for user-profile extraction.

- `name`: provider name, currently `openrouter`
- `model`: extraction model name
- `timeout_seconds`: request timeout for the provider

### `logger`

Controls runtime logging.

- `log_dir`: directory for log files
- `log_level`: one of `debug`, `info`, `warning`, `error`

### `storage`

Controls on-disk persisted memory.

- `data_dir`: required storage directory, resolved relative to the project root when not absolute

Structured user profile data is persisted at `storage.data_dir/user_model.json`.

### `mcp`

Controls MCP tool registration.

- `enabled_tools`: optional allowlist of exposed tools

Supported tool names:

- `get_user_profile`
- `search_memory`
- `ingest_turn`

### `vector_memory`

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

## FAQ

### How do I use a local embedding model via Ollama?

Seahorse ships with `nomic-embed-text` as the default, which is English-only. For mixed Chinese and English content, switch to a multilingual model.

Recommended local models:

| Model | Languages | Vector dims | Local memory | Notes |
|---|---|---|---|---|
| `nomic-embed-text` | English only | 768 | ~275 MB | Fast; default |
| `bge-m3` | 100+ | 1024 | ~1.2 GB | Reliable multilingual baseline |
| `qwen3-embedding:0.6b` | 100+ | 1024 | ~600 MB | Lightweight; better than bge-m3 |
| `qwen3-embedding:4b` | 100+ | 2560 | ~3 GB | Recommended balance of quality and resource use |
| `qwen3-embedding:8b` | 100+ | 4096 | ~5 GB (Q4) | Highest quality; requires 16 GB+ RAM |

**Steps to switch local models:**

**1. Pull the new model:**

```bash
docker compose exec ollama ollama pull qwen3-embedding:4b
```

**2. Remove the old model to free disk space (optional but recommended):**

```bash
docker compose exec ollama ollama rm nomic-embed-text
```

To list currently installed models:

```bash
docker compose exec ollama ollama list
```

**3. Update `config.yaml`:**

```yaml
vector_memory:
  embedding:
    provider: openai_compatible
    model: qwen3-embedding:4b
    base_url: http://localhost:11434/v1
    timeout_seconds: 30.0
```

No `api_key_env` is needed for local Ollama.

**4. Delete the existing Qdrant collection so it is rebuilt with the correct vector size:**

```bash
curl -X DELETE http://localhost:6333/collections/seahorse_memory
```

Then restart Seahorse. The collection is recreated automatically on the first ingest. Any previously stored vectors are lost and must be re-ingested.

**Note on memory usage:** Ollama loads a model into memory on the first request and unloads it automatically after **5 minutes of inactivity**. The model is reloaded on the next request, which adds a short delay for that first embedding call. During idle periods the model holds no memory.

---

### How do I use a third-party embedding service?

Seahorse supports any OpenAI-compatible embedding endpoint. No code changes are needed — only `config.yaml` and an environment variable for the API key.

**Qdrant collection rebuild is still required** when switching from a local model, because the vector dimension will change. Delete the existing collection before restarting:

```bash
curl -X DELETE http://localhost:6333/collections/seahorse_memory
```

#### OpenRouter

OpenRouter provides hosted access to models such as `qwen/qwen3-embedding-8b` through an OpenAI-compatible API. Set `api_key_env` to the name of whichever environment variable holds your OpenRouter embedding key.

```yaml
vector_memory:
  embedding:
    provider: openai_compatible
    model: qwen/qwen3-embedding-8b
    base_url: https://openrouter.ai/api/v1
    api_key_env: OPENROUTER_EMBEDDING_API_KEY
    timeout_seconds: 30.0
```

```bash
export OPENROUTER_EMBEDDING_API_KEY=your-key-here
```
