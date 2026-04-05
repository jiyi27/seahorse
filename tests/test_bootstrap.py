from __future__ import annotations

from pathlib import Path

from seahorse.bootstrap import build_app_container
from seahorse.infrastructure.config import AppPaths, load_provider_settings_from_env


def test_load_provider_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("SEAHORSE_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("SEAHORSE_TIMEOUT_SECONDS", "45")

    settings = load_provider_settings_from_env()

    assert settings.api_key == "test-key"
    assert settings.model == "openai/gpt-4.1-mini"
    assert settings.timeout_seconds == 45.0


def test_app_paths_resolve_expected_locations(tmp_path: Path) -> None:
    paths = AppPaths.from_project_root(tmp_path)

    assert paths.storage.core_rule_path == tmp_path / "data" / "core_rule.md"
    assert paths.storage.user_model_path == tmp_path / "data" / "user_model.md"
    assert paths.prompt_dir == tmp_path / "src" / "seahorse" / "prompts"


def test_build_app_container_wires_services(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("SEAHORSE_MODEL", "openai/gpt-4.1-mini")

    prompt_dir = tmp_path / "src" / "seahorse" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "user_model_extraction.md").write_text(
        "Return JSON.",
        encoding="utf-8",
    )

    container = build_app_container(tmp_path)

    assert container.paths.storage.data_dir == tmp_path / "data"
    assert container.recall_service is not None
    assert container.ingest_service is not None
