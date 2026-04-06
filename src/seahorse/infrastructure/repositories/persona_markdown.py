from __future__ import annotations

from pathlib import Path

from seahorse.domain.models import Persona


class MarkdownPersonaRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Persona:
        # Persona markdown is the configured source of the agent's behavior.
        content = self._path.read_text(encoding="utf-8").strip()
        return Persona(content=content)
