from __future__ import annotations

from pathlib import Path

from seahorse.domain.models import FactItem, TextItem, UserProfile
from seahorse.infrastructure.config import AppConfig, StoragePaths, USER_PROFILE_FILE_NAME
from seahorse.infrastructure.repositories.user_model_json import JSONUserProfileRepository


def test_storage_paths_build_from_config(tmp_path: Path) -> None:
    paths = StoragePaths.from_config(
        tmp_path,
        AppConfig.model_validate(
            {
                "storage": {
                    "data_dir": "memory-data",
                },
            }
        ).storage,
    )

    assert paths.data_dir == tmp_path / "memory-data"
    assert paths.user_model_path == tmp_path / "memory-data" / USER_PROFILE_FILE_NAME


def test_user_model_repository_returns_none_when_missing(tmp_path: Path) -> None:
    repository = JSONUserProfileRepository(tmp_path / "data" / USER_PROFILE_FILE_NAME)

    assert repository.load() is None


def test_user_model_repository_saves_and_loads_json(tmp_path: Path) -> None:
    path = tmp_path / "data" / USER_PROFILE_FILE_NAME
    repository = JSONUserProfileRepository(path)
    model = UserProfile(
        summary="Prefers concise answers.",
        facts=[FactItem(id="fact_001", category="identity", text="Uses Python")],
        preferences=[TextItem(id="preference_001", text="Concise answers")],
    )

    repository.save(model)
    loaded = repository.load()

    assert path.exists()
    assert loaded == model
