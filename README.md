## Seahorse

Seahorse is a single-user memory service for agent systems. It helps agents retain user profile facts, ingest session memory, and search past context over MCP or HTTP.

## Configuration

Seahorse uses two configuration sources:

- `config.yaml` in the project root for non-secret application settings
- environment variables for secrets only

Required environment variables:

- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY` only when `vector_memory.enabled` is true and `embedding.api_key_env`
  points to that variable

The default [`config.yaml`](/Users/david/codes/agent/seahorse/config.yaml) covers:

- provider name, model, and timeout
- log directory and log level
- MCP tool registration
- memory search defaults such as configured result count
- storage directory for user memory
- optional vector-memory settings, embedding settings, and Qdrant connection settings

Secrets are not read from `.env` files. Export `OPENROUTER_API_KEY` in the shell or process environment before startup. Copy [`config.yaml.example`](/Users/david/codes/agent/seahorse/config.yaml.example) to `config.yaml` if you want to start from the documented template.

`storage` is required in `config.yaml`. Seahorse expects `storage.data_dir` to be written explicitly so the memory location is always visible in the checked-in config.

`mcp.enabled_tools` is optional. Use it when you want Seahorse to register only a subset of tools for a given agent. If omitted, Seahorse registers `get_user_profile`, `search_memory`, and `ingest_turn`.

`memory_search.top_k` is optional. It controls how many results `search_memory` returns. This stays in server config rather than the tool schema so the agent only supplies the recall query, not retrieval tuning knobs.

Startup is fail-fast. Seahorse exits during bootstrap if:

- `OPENROUTER_API_KEY` is missing
- the configured provider requires fields that are not set
- vector memory is enabled but embedding or Qdrant settings are incomplete
- the prompt file is missing
- the YAML structure or field values are invalid

The persisted user model is stored as structured JSON in `storage.data_dir/user_model.json`.

## Vector Memory

Seahorse now supports optional transcript vector indexing backed by Qdrant.

When `vector_memory.enabled` is true:

- `/memory/sessions` still updates the user profile
- the same ingest call also chunks the conversation and writes vector memory
- `/memory/search` prefers vector search first
- `/health` reports embedding and Qdrant status

For a local setup and verification guide, see
[docs/vector-memory-runbook.md](/Users/david/codes/agent/seahorse/docs/vector-memory-runbook.md).

## Current Scope

The current skeleton implements Phase 1 from [docs/architecture_v2.md](/Users/david/codes/agent/seahorse/docs/architecture_v2.md):

1. Domain models and protocols
2. Application services for ingest and recall
3. A deterministic user-model merger
4. Structured JSON storage for `user_model`
5. A lightweight provider and LLM extractor boundary
6. Bootstrap wiring for services and tool adapters
7. MCP and HTTP transport adapters
8. Minimal unit tests

Future phases will add transport adapters and runtime integration.

## Common Commands

The repository includes a small `Makefile` for common workflows:

- `make sync` installs dependencies with `uv`
- `make test` runs the test suite
- `make run` starts the HTTP server on `127.0.0.1:8081`
- `make run-mcp` starts the Seahorse MCP server over stdio for manual debugging

You can also run the packaged entrypoints directly:

- `uv run seahorse-http` starts the HTTP server on `127.0.0.1:8081`
- `uv run seahorse-mcp` starts the MCP server over stdio
