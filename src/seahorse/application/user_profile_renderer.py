from __future__ import annotations

from seahorse.domain.models import FactCategory, FactItem, TextItem, UserProfile

FACT_CATEGORY_TITLES: dict[FactCategory, str] = {
    "identity": "Identity",
    "personality": "Personality",
    "social": "Social",
    "interests": "Interests",
    "values": "Values",
    "life_situation": "Life Situation",
    "note": "Note",
}


class UserProfileRenderer:
    _SUMMARY_HEADER = "## Summary"
    _FACTS_HEADER = "## Facts"
    _PREFERENCES_HEADER = "## Preferences"
    _CONSTRAINTS_HEADER = "## Constraints"

    def render_markdown(self, user_profile: UserProfile) -> str:
        parts: list[str] = []

        summary = user_profile.summary.strip()
        if summary:
            parts.extend([self._SUMMARY_HEADER, summary])

        parts.extend(self._render_facts_section(user_profile.facts))
        parts.extend(
            self._render_text_section(self._PREFERENCES_HEADER, user_profile.preferences)
        )
        parts.extend(
            self._render_text_section(self._CONSTRAINTS_HEADER, user_profile.constraints)
        )

        if not parts:
            return ""
        return "\n\n".join(parts).strip() + "\n"

    def _render_facts_section(self, facts: list[FactItem]) -> list[str]:
        rendered_groups: list[str] = []
        for category, title in FACT_CATEGORY_TITLES.items():
            items = [item.text for item in facts if item.category == category]
            if not items:
                continue
            rendered_groups.append(f"### {title}\n" + "\n".join(f"- {item}" for item in items))
        if not rendered_groups:
            return []
        return [self._FACTS_HEADER, "\n\n".join(rendered_groups)]

    def _render_text_section(self, header: str, items: list[TextItem]) -> list[str]:
        if not items:
            return []
        rendered_items = "\n".join(f"- {item.text}" for item in items)
        return [header, rendered_items]
