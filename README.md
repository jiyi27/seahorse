## Seahorse

Seahorse is a single-user memory service for agent systems.

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
