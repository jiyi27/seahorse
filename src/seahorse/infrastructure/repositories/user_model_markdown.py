from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from seahorse.domain.models import UserModel


class MarkdownUserModelRepository:
    _METADATA_PATTERN = re.compile(
        r"^<!--\s*seahorse:user-model\s+version:(?P<version>\d+)"
        r"(?:\s+updated_at:(?P<updated_at>[^\s]+))?\s*-->\n?",
    )

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> UserModel | None:
        if not self._path.exists():
            return None

        raw_content = self._path.read_text(encoding="utf-8")
        content, version, updated_at = self._deserialize(raw_content)
        if not content.strip():
            return None

        return UserModel(content=content, updated_at=updated_at, version=version)

    def save(self, model: UserModel) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(self._serialize(model), encoding="utf-8")

    def _deserialize(self, raw_content: str) -> tuple[str, int, datetime]:
        version = 1
        updated_at = datetime.fromtimestamp(self._path.stat().st_mtime).astimezone()
        content = raw_content
        match = self._METADATA_PATTERN.match(raw_content)
        if match:
            version = int(match.group("version"))
            if match.group("updated_at"):
                updated_at = datetime.fromisoformat(match.group("updated_at"))
            content = raw_content[match.end() :]
        return content.strip(), version, updated_at

    def _serialize(self, model: UserModel) -> str:
        metadata = (
            "<!-- seahorse:user-model "
            f"version:{model.version} "
            f"updated_at:{model.updated_at.isoformat()} -->\n"
        )
        content = model.content.rstrip() + "\n"
        return metadata + content
