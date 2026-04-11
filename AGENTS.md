# Agent Guidance For Seahorse

This file is written for coding agents working in this repository. Follow these rules by default unless the user explicitly asks for something else. The guidance here may become stale as the codebase evolves, so if the repository and this file disagree, follow the code, call out the mismatch, and suggest updating this document.

## Purpose

- Seahorse is a single-user memory service for agent systems.
- Keep the MVP small. Do not add multi-user support, vector storage, embeddings, or LangChain unless explicitly asked.

## Structure

The codebase is organized by layer:

- `src/seahorse/domain`: core models and repository or service interfaces
- `src/seahorse/application`: orchestration and merge logic
- `src/seahorse/infrastructure`: config loading, repositories, providers, extractors, vector integrations
- `src/seahorse/api`: HTTP and MCP transport adapters
- `src/seahorse/prompts`: prompt templates used by extraction flows
- `tests`: wiring, regression, and adapter tests

## Config

- Prefer explicit values in `config.yaml` over code defaults for anything that affects operational behavior. Code defaults are acceptable only for genuinely optional or low-stakes settings.
- Keep each config section as its own Pydantic model with its own field validators. Do not merge unrelated config into one model.

## Coding Style

- If the same string, number, metadata field, or structural assumption appears in more than one place, extract it to a shared constant, `Enum`, helper, or schema definition before writing the second use.
- Keep prompt text, hint text, and other reusable long strings in one clear location rather than scattering them across multiple files.
- Keep functions focused. Do not mix unrelated responsibilities in one function when that would make the code harder to extend, test, or reuse.
- Comments should explain intent or constraints, not restate obvious code behavior.

## Testing

- Write unit tests for pure logic with meaningful branching or edge cases.
- Use integration or wiring tests when the risk is config loading, service composition, repository behavior, or API/MCP adapters.
- Add regression tests when changing merge logic, prompt parsing, config loading, or storage format.
- Check `pyproject.toml` or `Makefile` for available commands.

## Final Phase

- After completing a task, verify it works. Run existing tests to confirm no regressions and no layer boundaries are broken.
- Do not add new tests by default. First check if existing tests already cover the changed behavior. Only add tests when the change is high-risk — core logic, complex branching, or merge/parse behavior, etc.
- If code changed, include a suggested commit message:
  - Format: `<type>: <summary>` or `<type>(<scope>): <summary>`
  - Common types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
  - Short, specific, and lowercase.
