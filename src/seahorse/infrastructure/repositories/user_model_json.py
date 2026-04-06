from __future__ import annotations

from pathlib import Path
import re

from pydantic import ValidationError

from seahorse.domain.models import FactItem, TextItem, UserModel

LEGACY_MARKDOWN_SUFFIX = ".md"
JSON_SUFFIX = ".json"
LEGACY_METADATA_PATTERN = re.compile(
    r"^<!--\s*seahorse:user-model\s+version:(?P<version>\d+)"
    r"(?:\s+updated_at:(?P<updated_at>[^\s]+))?\s*-->\n?",
)
SUMMARY_HEADER = "## Summary"
FACTS_HEADER = "## Facts"
PREFERENCES_HEADER = "## Preferences"
CONSTRAINTS_HEADER = "## Constraints"
LEGACY_FACT_PREFIXES: tuple[tuple[str, str], ...] = (
    ("[Identity]", "identity"),
    ("[Personality]", "personality"),
    ("[Social]", "social"),
    ("[Interests]", "interests"),
    ("[Values]", "values"),
    ("[Life Situation]", "life_situation"),
    ("[Note]", "note"),
)


class JSONUserModelRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> UserModel | None:
        if self._path.exists():
            return self._load_json()

        legacy_path = self._legacy_markdown_path()
        if legacy_path is not None and legacy_path.exists():
            return self._load_legacy_markdown(legacy_path)

        return None

    def _load_json(self) -> UserModel | None:
        try:
            raw_content = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Failed to read user model storage: {self._path}") from exc

        try:
            return UserModel.model_validate_json(raw_content)
        except ValidationError as exc:
            raise RuntimeError("User model storage contains invalid JSON") from exc

    def save(self, model: UserModel) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Failed to write user model storage: {self._path}") from exc

    def _legacy_markdown_path(self) -> Path | None:
        if self._path.suffix != JSON_SUFFIX:
            return None
        return self._path.with_suffix(LEGACY_MARKDOWN_SUFFIX)

    def _load_legacy_markdown(self, path: Path) -> UserModel | None:
        try:
            raw_content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Failed to read legacy user model storage: {path}") from exc

        content = self._strip_legacy_metadata(raw_content)
        if not content.strip():
            return None
        return self._parse_legacy_markdown_content(content)

    def _strip_legacy_metadata(self, raw_content: str) -> str:
        match = LEGACY_METADATA_PATTERN.match(raw_content)
        if not match:
            return raw_content.strip()
        return raw_content[match.end() :].strip()

    def _parse_legacy_markdown_content(self, content: str) -> UserModel:
        sections: dict[str, str | list[str]] = {
            "summary": "",
            "facts": [],
            "preferences": [],
            "constraints": [],
        }
        summary_lines: list[str] = []
        current_section: str | None = None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line == SUMMARY_HEADER:
                current_section = "summary"
                continue
            if line == FACTS_HEADER:
                current_section = "facts"
                continue
            if line == PREFERENCES_HEADER:
                current_section = "preferences"
                continue
            if line == CONSTRAINTS_HEADER:
                current_section = "constraints"
                continue
            if not current_section or not line:
                continue
            if current_section == "summary":
                if line != "No summary yet.":
                    summary_lines.append(line)
                continue
            if not line.startswith("- "):
                continue
            item_text = line[2:].strip()
            if item_text == "None":
                continue
            section_items = sections[current_section]
            assert isinstance(section_items, list)
            section_items.append(item_text)

        sections["summary"] = "\n".join(summary_lines).strip()
        return UserModel(
            summary=sections["summary"],
            facts=self._build_facts(sections["facts"]),
            preferences=self._build_text_items("preference", sections["preferences"]),
            constraints=self._build_text_items("constraint", sections["constraints"]),
        )

    def _build_facts(self, items: object) -> list[FactItem]:
        assert isinstance(items, list)
        facts: list[FactItem] = []
        for index, item in enumerate(items, start=1):
            category, text = self._split_legacy_fact(item)
            facts.append(FactItem(id=f"fact_{index:03d}", category=category, text=text))
        return facts

    def _build_text_items(self, prefix: str, items: object) -> list[TextItem]:
        assert isinstance(items, list)
        return [
            TextItem(id=f"{prefix}_{index:03d}", text=item)
            for index, item in enumerate(items, start=1)
        ]

    def _split_legacy_fact(self, item: str) -> tuple[str, str]:
        for prefix, category in LEGACY_FACT_PREFIXES:
            if item.startswith(prefix):
                return category, item.removeprefix(prefix).strip()
        return "note", item
