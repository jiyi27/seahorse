# Agent Guidance For Seahorse

This file is written for coding agents working in this repository. Follow these rules by default unless the user explicitly asks for something else. The guidance here may become stale as the codebase evolves, so if the repository and this file disagree, follow the code, call out the mismatch, and suggest updating this document.

## Purpose

- Seahorse is a single-user memory service for agent systems.
- Keep the MVP small. Do not add multi-user support, vector storage, embeddings, or LangChain unless explicitly asked.

## Structure

- `src/seahorse/domain/`: domain models and interfaces only.
- `src/seahorse/application/`: orchestration and merge logic.
- `src/seahorse/infrastructure/`: config, repositories, provider, extractor.
- `src/seahorse/api/`: MCP and HTTP adapters only.
- `src/seahorse/prompts/`: prompt templates.
- `tests/`: regression and wiring tests.
- `docs/tool-design.md`: current checked-in design reference.

## Rules

- Preserve the layer boundaries. Do not put business logic in `api/` or provider details in `domain/`.
- Read env vars only in `src/seahorse/infrastructure/config.py`.
- `UserModelExtractor` owns prompt assembly and provider calls.
- `UserModelMerger` owns merge policy.
- `UserModelRenderer` owns markdown rendering for external recall output.
- `IngestService` and `RecallService` are the orchestration boundary.
- Keep failures concise and actionable.
- Do not overwrite unrelated local changes.

## Coding Style

- Use `snake_case` for variables, functions, and modules; use `PascalCase` for classes.
- If the same string, number, metadata field, or structural assumption appears in more than one place, extract it to a shared constant, `Enum`, helper, or schema definition before writing the second use.
- Keep prompt text, hint text, and other reusable long strings in one clear location rather than scattering them across multiple files.
- Config schema values must be accepted exactly; undocumented aliases are forbidden.
- Keep functions focused. Do not mix unrelated responsibilities in one function when that would make the code harder to extend, test, or reuse.
- Comments should explain intent or constraints, not restate obvious code behavior.
- Persist the user model as structured JSON. Do not make markdown the source of truth for merge logic.
- Store fact categories as structured fields, not as text prefixes like `[Identity]`.

## Config

- Required env vars: `OPENROUTER_API_KEY`.
- Keep configuration minimal. Prefer code defaults over adding new env vars unless there is a real operational need.
- If config or storage behavior changes, update `config.yaml.example` and `README.md`.

## Testing

- Mock provider calls in tests. Never hit real external services.
- Add regression tests when changing merge logic, prompt parsing, config loading, or storage format.
- Useful commands: `uv sync`, `uv run pytest`, `uv run seahorse-mcp`, `uv run seahorse-http`.

## Final Phase

- End each task with verification.
- Choose verification based on risk and prefer the lightest check that proves the change works.
- Do not add unit tests for every function.
- Write unit tests for core pure logic and code with meaningful branching or edge cases.
- Prefer integration or wiring tests when the main risk is config loading, service composition, repositories, or API/MCP adapter behavior.
- If no automated test fits, do a small manual verification step and report it clearly.
- Include a suggested commit message in the final response.
