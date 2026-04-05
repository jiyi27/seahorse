from __future__ import annotations

from collections import OrderedDict

from seahorse.domain.models import UserModel, UserModelPatch, utc_now


class UserModelMerger:
    """Merge structured patches into a deterministic Markdown document."""

    _SUMMARY_HEADER = "## Summary"
    _FACTS_HEADER = "## Facts"
    _PREFERENCES_HEADER = "## Preferences"
    _CONSTRAINTS_HEADER = "## Constraints"

    def merge(self, current: UserModel | None, patch: UserModelPatch) -> UserModel:
        existing = self._parse_markdown(current.content if current else "")

        summary = patch.summary.strip() or existing["summary"]
        facts = self._merge_list(
            existing["facts"], patch.facts_to_add, patch.stale_items_to_remove
        )
        preferences = self._merge_list(
            existing["preferences"],
            patch.preferences_to_add,
            patch.stale_items_to_remove,
        )
        constraints = self._merge_list(
            existing["constraints"],
            patch.constraints_to_add,
            patch.stale_items_to_remove,
        )

        content = self._render_markdown(summary, facts, preferences, constraints)
        version = 1 if current is None else current.version + 1

        return UserModel(content=content, updated_at=utc_now(), version=version)

    def _parse_markdown(self, content: str) -> dict[str, str | list[str]]:
        sections: dict[str, str | list[str]] = {
            "summary": "",
            "facts": [],
            "preferences": [],
            "constraints": [],
        }
        current_section: str | None = None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line == self._SUMMARY_HEADER:
                current_section = "summary"
                continue
            if line == self._FACTS_HEADER:
                current_section = "facts"
                continue
            if line == self._PREFERENCES_HEADER:
                current_section = "preferences"
                continue
            if line == self._CONSTRAINTS_HEADER:
                current_section = "constraints"
                continue
            if not current_section or not line:
                continue
            if current_section == "summary":
                sections["summary"] = (
                    f"{sections['summary']} {line}".strip()
                    if sections["summary"]
                    else line
                )
                continue
            if line.startswith("- "):
                section_items = sections[current_section]
                assert isinstance(section_items, list)
                section_items.append(line[2:].strip())

        return sections

    def _merge_list(
        self, existing: list[str], additions: list[str], removals: list[str]
    ) -> list[str]:
        normalized_removals = {item.strip() for item in removals if item.strip()}
        items = [item for item in existing if item.strip() not in normalized_removals]
        items.extend(item.strip() for item in additions if item.strip())

        ordered: OrderedDict[str, None] = OrderedDict()
        for item in items:
            if item:
                ordered[item] = None
        return list(ordered.keys())

    def _render_markdown(
        self,
        summary: str,
        facts: list[str],
        preferences: list[str],
        constraints: list[str],
    ) -> str:
        parts = [self._SUMMARY_HEADER, summary or "No summary yet."]
        parts.extend(self._render_list_section(self._FACTS_HEADER, facts))
        parts.extend(self._render_list_section(self._PREFERENCES_HEADER, preferences))
        parts.extend(self._render_list_section(self._CONSTRAINTS_HEADER, constraints))
        return "\n\n".join(parts).strip() + "\n"

    def _render_list_section(self, header: str, items: list[str]) -> list[str]:
        rendered_items = "\n".join(f"- {item}" for item in items) if items else "- None"
        return [header, rendered_items]
