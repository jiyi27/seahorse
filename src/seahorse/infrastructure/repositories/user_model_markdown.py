from __future__ import annotations

from pathlib import Path
import re

from seahorse.domain.models import UserModel, utc_now


class MarkdownUserModelRepository:
    _METADATA_PATTERN = re.compile(
        r"^<!--\s*seahorse:user-model\s+version:(?P<version>\d+)\s*-->\n?",
    )

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> UserModel | None:
        if not self._path.exists():
            return None

        raw_content = self._path.read_text(encoding="utf-8")
        content, version = self._deserialize(raw_content)
        if not content.strip():
            return None

        return UserModel(content=content, updated_at=utc_now(), version=version)

    def save(self, model: UserModel) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(self._serialize(model), encoding="utf-8")

    def _deserialize(self, raw_content: str) -> tuple[str, int]:
        version = 1
        content = raw_content
        match = self._METADATA_PATTERN.match(raw_content)
        if match:
            version = int(match.group("version"))
            content = raw_content[match.end() :]
        return content.strip(), version

    def _serialize(self, model: UserModel) -> str:
        metadata = f"<!-- seahorse:user-model version:{model.version} -->\n"
        content = model.content.rstrip() + "\n"
        return metadata + content
