from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from seahorse.domain.models import UserModel
from seahorse.infrastructure.config import StoragePaths
from seahorse.infrastructure.repositories.core_rule_markdown import (
    DEFAULT_CORE_RULE_CONTENT,
    MarkdownCoreRuleRepository,
)
from seahorse.infrastructure.repositories.user_model_markdown import (
    MarkdownUserModelRepository,
)


def test_storage_paths_build_from_project_root(tmp_path: Path) -> None:
    paths = StoragePaths.from_project_root(tmp_path)

    assert paths.data_dir == tmp_path / "data"
    assert paths.core_rule_path == tmp_path / "data" / "core_rule.md"
    assert paths.user_model_path == tmp_path / "data" / "user_model.md"


def test_core_rule_repository_initializes_default_file_when_missing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "data" / "core_rule.md"
    repository = MarkdownCoreRuleRepository(path)

    core_rule = repository.load()

    assert path.exists()
    assert core_rule.content == DEFAULT_CORE_RULE_CONTENT.strip()
    assert path.read_text(encoding="utf-8") == DEFAULT_CORE_RULE_CONTENT.strip() + "\n"


def test_user_model_repository_returns_none_when_missing(tmp_path: Path) -> None:
    repository = MarkdownUserModelRepository(tmp_path / "data" / "user_model.md")

    assert repository.load() is None


def test_user_model_repository_saves_and_loads_markdown(tmp_path: Path) -> None:
    path = tmp_path / "data" / "user_model.md"
    repository = MarkdownUserModelRepository(path)
    updated_at = datetime(2026, 4, 5, 10, 30, tzinfo=timezone.utc)
    model = UserModel(
        content="## Summary\n\nPrefers concise answers.\n",
        updated_at=updated_at,
        version=3,
    )

    repository.save(model)
    loaded = repository.load()

    assert path.exists()
    assert loaded is not None
    assert loaded.version == 3
    assert loaded.updated_at == updated_at
    assert loaded.content == "## Summary\n\nPrefers concise answers."
    assert path.read_text(encoding="utf-8") == (
        "<!-- seahorse:user-model version:3 "
        "updated_at:2026-04-05T10:30:00+00:00 -->\n"
        "## Summary\n\nPrefers concise answers.\n"
    )


def test_user_model_repository_loads_legacy_metadata_without_updated_at(
    tmp_path: Path,
) -> None:
    path = tmp_path / "data" / "user_model.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<!-- seahorse:user-model version:2 -->\n"
        "## Summary\n\nLegacy content.\n",
        encoding="utf-8",
    )
    repository = MarkdownUserModelRepository(path)

    loaded = repository.load()

    assert loaded is not None
    assert loaded.version == 2
    assert loaded.content == "## Summary\n\nLegacy content."
