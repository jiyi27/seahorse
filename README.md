## Seahorse

Seahorse is a single-user memory service for agent systems.

## Configuration

Copy `.env.example` to `.env` and set at least:

- `OPENROUTER_API_KEY`
- `SEAHORSE_MODEL`

Optional settings:

- `SEAHORSE_LOG_DIR`
- `SEAHORSE_LOG_LEVEL`

The current implementation is wired to OpenRouter. The API base URL, request
timeout, and attribution headers are internal defaults rather than user-facing
configuration.

The current skeleton implements Phase 1 from [docs/architecture_v2.md](/Users/david/codes/agent/seahorse/docs/architecture_v2.md):

1. Domain models and protocols
2. Application services for ingest and recall
3. A deterministic user-model merger
4. Markdown repositories for `core_rule` and `user_model`
5. A lightweight provider and LLM extractor boundary
6. Bootstrap wiring for services and tool adapters
7. MCP and HTTP transport adapters
8. Minimal unit tests

Future phases will add transport adapters and runtime integration.

## Common Commands

The repository includes a small `Makefile` for common workflows:

- `make sync` installs dependencies with `uv`
- `make test` runs the test suite
- `make run` starts the HTTP server on `127.0.0.1:8000`
- `make run-mcp` starts the Seahorse MCP server over stdio for manual debugging
