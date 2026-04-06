from __future__ import annotations

from pathlib import Path

from seahorse.domain.models import FactItem, TextItem, UserModel
from seahorse.infrastructure.config import AppConfig, StoragePaths, USER_MODEL_FILE_NAME
from seahorse.infrastructure.repositories.persona_markdown import MarkdownPersonaRepository
from seahorse.infrastructure.repositories.user_model_json import JSONUserModelRepository


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


def test_persona_repository_reads_existing_persona_file(tmp_path: Path) -> None:
    path = tmp_path / "personas" / "default.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Core Rule\n\nBe precise.\n", encoding="utf-8")
    repository = MarkdownPersonaRepository(path)

    persona = repository.load()

    assert persona.content == "# Core Rule\n\nBe precise."


def test_user_model_repository_returns_none_when_missing(tmp_path: Path) -> None:
    repository = JSONUserModelRepository(tmp_path / "data" / USER_MODEL_FILE_NAME)

    assert repository.load() is None


def test_user_model_repository_saves_and_loads_json(tmp_path: Path) -> None:
    path = tmp_path / "data" / USER_MODEL_FILE_NAME
    repository = JSONUserModelRepository(path)
    model = UserModel(
        summary="Prefers concise answers.",
        facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    repository.save(model)
    loaded = repository.load()

    assert path.exists()
    assert loaded == model
