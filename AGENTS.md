# Agent Guidance For Seahorse

This file is written for coding agents working in this repository. Follow these rules by default unless the user explicitly asks for something else. If the repository and this file disagree, follow the code, call out the mismatch, and suggest updating this document.

Seahorse is a single-user memory service for agent systems.

## Structure

- `src/seahorse/domain`: core models and repository or service interfaces
- `src/seahorse/application`: orchestration and merge logic
- `src/seahorse/infrastructure`: config loading, repositories, providers, extractors, vector integrations
- `src/seahorse/api`: HTTP and MCP transport adapters
- `src/seahorse/prompts`: prompt templates used by extraction flows
- `tests`

## Testing

This section describes the testing philosophy for this project. The default is to not write tests unless the rationale below clearly applies.

Tests are worth writing only when breaking the code would damage core memory behavior: user profile merge correctness, extraction or parsing boundaries, ingest chunking, retrieval deduplication or ranking limits, or tool responses that define the agent-facing contract. Everything else is not worth testing.

Good candidates for unit tests:
- `application/user_profile_merger.py` and `application/user_profile_ingest_service.py` — merge rules, add or remove behavior, no-op patches, persistence only when state changes
- `ingest/` modules — conversation block grouping, block rendering, child chunk creation, stable IDs, payload shape
- `retrieval/` modules — parent-hit rendering, deduplication, max-block truncation, result shaping
- `tools/` modules only when they add user-visible contract logic beyond a thin pass-through
- extractor parsing only where Seahorse-owned prompt or response normalization logic can regress without any external dependency

Integration tests: use them sparingly, only for one user-visible invariant across the core path. Prefer fakes over real providers, stores, HTTP servers, or MCP transports.

Do not test: config loading, secrets loading, bootstrap wiring, logging, HTTP routing, FastAPI middleware, MCP server registration, provider request formatting, embedding client transport, Qdrant adapter compatibility, repository read or write plumbing, or any layer whose only logic delegates to something already tested.

Before writing any new test, stop and tell the user: what invariant the test protects, why it matters to Seahorse's core memory behavior, and why existing tests do not already cover it. Do not proceed until the user confirms.

When tightening or simplifying the suite, prefer deleting adapter or wiring tests before deleting core-logic tests. Check `pyproject.toml` or `Makefile` for available commands.

## Final Phase

- After completing a task, verify it works. Run existing tests to confirm no regressions and no layer boundaries are broken.
- Do not add new tests by default. First check if existing tests already cover the changed behavior. Only add tests when the change is high-risk — core logic, complex branching, or merge/parse behavior, etc.
- If code changed, include a suggested commit message:
  - Format: `<type>: <summary>` or `<type>(<scope>): <summary>`
  - Common types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
  - Short, specific, and lowercase.
