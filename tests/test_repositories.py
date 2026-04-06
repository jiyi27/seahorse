from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from seahorse.domain.models import UserModel
from seahorse.infrastructure.config import AppConfig, StoragePaths, USER_MODEL_FILE_NAME
from seahorse.infrastructure.repositories.core_rule_markdown import (
    MarkdownCoreRuleRepository,
)
from seahorse.infrastructure.repositories.user_model_markdown import (
    MarkdownUserModelRepository,
)


def test_storage_paths_build_from_config(tmp_path: Path) -> None:
    paths = StoragePaths.from_config(
        tmp_path,
        AppConfig.model_validate(
            {
                "storage": {
                    "data_dir": "memory-data",
                    "persona_dir": "personas",
                    "persona_name": "default",
                }
            }
        ).storage,
    )

    assert paths.data_dir == tmp_path / "memory-data"
    assert paths.user_model_path == tmp_path / "memory-data" / USER_MODEL_FILE_NAME


def test_core_rule_repository_reads_existing_persona_file(tmp_path: Path) -> None:
    path = tmp_path / "personas" / "default.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Core Rule\n\nBe precise.\n", encoding="utf-8")
    repository = MarkdownCoreRuleRepository(path)

    core_rule = repository.load()

    assert core_rule.content == "# Core Rule\n\nBe precise."


def test_user_model_repository_returns_none_when_missing(tmp_path: Path) -> None:
    repository = MarkdownUserModelRepository(tmp_path / "data" / USER_MODEL_FILE_NAME)

    assert repository.load() is None


def test_user_model_repository_saves_and_loads_markdown(tmp_path: Path) -> None:
    path = tmp_path / "data" / USER_MODEL_FILE_NAME
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
    path = tmp_path / "data" / USER_MODEL_FILE_NAME
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
