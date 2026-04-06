from __future__ import annotations

from pathlib import Path

from seahorse.domain.models import CoreRule, utc_now


class MarkdownPersonaRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> CoreRule:
        # Persona markdown is the configured source of the agent's core rule.
        content = self._path.read_text(encoding="utf-8").strip()
        return CoreRule(content=content, updated_at=utc_now())
