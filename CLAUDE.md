# Repository Guidelines

## Project Structure

- `src/seahorse/domain/` — domain models and repository/service interfaces. No infrastructure dependencies allowed here.
- `src/seahorse/application/` — application services (`IngestService`, `RecallService`, `UserModelMerger`). Coordinate domain and infrastructure through injected interfaces.
- `src/seahorse/infrastructure/` — concrete implementations: Markdown repositories, LLM provider, extractor, config loading.
- `src/seahorse/api/` — transport adapters (MCP tools, HTTP routes). Validate input, call application services, return results. No business logic here.
- `src/seahorse/prompts/` — prompt templates as Markdown files.
- `data/` — runtime storage for `core_rule.md` and `user_model.md`.
- `tests/` — test suite covering domain, merger, services, and API adapters.
- `docs/` — architecture documentation. `architecture_v2.md` is the current reference.

## Development Commands

- `uv sync` — install dependencies into the local virtual environment.
- `uv run seahorse` — run through the packaged entry point.
- `uv run pytest` — run the test suite.

## Architecture & Design Patterns

- **Strict dependency direction**: `api` → `application` → `domain`. Infrastructure implements domain interfaces and is wired at startup via constructor injection. Domain imports nothing from infrastructure.
- **Single-user only**: There is no multi-user routing, tenancy, or `user_id`. Do not introduce them.
- **Narrow repository interfaces**: `CoreRuleRepository` and `UserModelRepository` are separate Protocol-based interfaces. Do not introduce a generic `StorageBackend` abstraction.
- **Extractor owns prompt assembly**: `UserModelExtractor` is responsible for prompt construction, provider calls, and parsing output into `UserModelPatch`. It does not touch repositories or transport concerns.
- **Merger owns merge policy**: `UserModelMerger` applies `UserModelPatch` to the current `UserModel`. Keeping this separate from the extractor means prompt changes do not force persistence changes.
- **Application services are the only orchestration point**: `IngestService` and `RecallService` are the sole place where repositories, extractors, and pipeline hooks are coordinated.
- **Episode pipeline is a no-op hook for MVP**: The `EpisodePipeline` interface exists, but the MVP implementation is `NoopEpisodePipeline`. Do not add vector storage, embeddings, or LangChain until this hook is wired to a real implementation.
- **Config at the boundary**: Read environment variables in `infrastructure/config.py`. Avoid scattered `os.getenv()` calls in other modules.
- **Actionable failures**: Raise concise `RuntimeError` for user-fixable issues such as missing config, invalid input, or upstream API errors.
- **Standard-library first**: Prefer the Python standard library unless an added dependency clearly improves correctness or maintainability.

## Testing Guidelines

- Test layers in isolation: fake repositories and extractors for service tests; real file I/O for repository tests; thin wiring checks for API tests.
- Do not let tests call real LLM providers or external services. Mock at the `LLMProvider` boundary.
- Test `UserModelMerger` with pure unit tests — no I/O, no provider calls.
- Add regression tests when changing merge logic, prompt parsing, or repository file layout.

## Configuration & Security

- Document required environment variables in `.env.example` whenever adding a new setting.
- Validate required configuration early in startup and fail fast with a clear error message.

## Change Guidance For LLM Agents

- Preserve the layered architecture. Do not let infrastructure details leak into domain or application code.
- When adding a new feature, identify which layer it belongs to before writing code. Transport changes go in `api/`. Storage changes go in `infrastructure/repositories/`. Business logic changes go in `application/` or `domain/`.
- Keep the MVP scope. Do not add episode persistence, vector storage, or multi-user support without explicit instruction.
- Do not overwrite unrelated local modifications in this repository. The worktree may already contain user changes.
- When changing the data model or storage format, check whether existing `data/*.md` files need a migration path.

## Commit Message Guidelines

- Format: `<type>: <summary>` or `<type>(<scope>): <summary>`.
- Common types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- Keep messages short, specific, and lowercase.

## Final Response Requirement For LLM Agents

- After any change to code, tests, docs, or configuration files, include one suggested commit message in the final response.
- Follow the commit message format above.
- Put it on its own line prefixed with `Suggested commit message:`.
