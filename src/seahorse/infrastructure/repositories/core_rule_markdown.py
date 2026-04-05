from __future__ import annotations

from pathlib import Path

from seahorse.domain.models import CoreRule, utc_now


DEFAULT_CORE_RULE_CONTENT = """# Core Rule

You are a pragmatic, precise agent.
Prefer clear reasoning, direct answers, and minimal unnecessary verbosity.
"""


class MarkdownCoreRuleRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> CoreRule:
        if not self._path.exists():
            self._initialize_default_file()

        content = self._path.read_text(encoding="utf-8").strip()
        return CoreRule(content=content, updated_at=utc_now())

    def _initialize_default_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(DEFAULT_CORE_RULE_CONTENT.strip() + "\n", encoding="utf-8")
