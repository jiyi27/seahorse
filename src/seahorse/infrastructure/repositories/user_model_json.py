from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from seahorse.domain.models import UserProfile


class JSONUserProfileRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> UserProfile | None:
        if self._path.exists():
            return self._load_json()
        return None

    def _load_json(self) -> UserProfile | None:
        try:
            raw_content = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Failed to read user model storage: {self._path}") from exc

        try:
            return UserProfile.model_validate_json(raw_content)
        except ValidationError as exc:
            raise RuntimeError("User model storage contains invalid JSON") from exc

    def save(self, model: UserProfile) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Failed to write user model storage: {self._path}") from exc
