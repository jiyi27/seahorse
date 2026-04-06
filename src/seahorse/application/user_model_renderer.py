from __future__ import annotations

from seahorse.domain.models import FactCategory, FactItem, TextItem, UserModel

FACT_CATEGORY_TITLES: dict[FactCategory, str] = {
    "identity": "Identity",
    "personality": "Personality",
    "social": "Social",
    "interests": "Interests",
    "values": "Values",
    "life_situation": "Life Situation",
    "note": "Note",
}


class UserModelRenderer:
    _SUMMARY_HEADER = "## Summary"
    _FACTS_HEADER = "## Facts"
    _PREFERENCES_HEADER = "## Preferences"
    _CONSTRAINTS_HEADER = "## Constraints"

    def render_markdown(self, user_model: UserModel) -> str:
        parts = [self._SUMMARY_HEADER, user_model.summary.strip()]
        parts.extend(self._render_facts_section(user_model.facts))
        parts.extend(self._render_text_section(self._PREFERENCES_HEADER, user_model.preferences))
        parts.extend(self._render_text_section(self._CONSTRAINTS_HEADER, user_model.constraints))
        return "\n\n".join(parts).strip() + "\n"

    def _render_facts_section(self, facts: list[FactItem]) -> list[str]:
        rendered_groups: list[str] = []
        for category, title in FACT_CATEGORY_TITLES.items():
            items = [item.text for item in facts if item.category == category]
            if not items:
                continue
            rendered_groups.append(f"### {title}\n" + "\n".join(f"- {item}" for item in items))
        return [self._FACTS_HEADER, "\n\n".join(rendered_groups)]

    def _render_text_section(self, header: str, items: list[TextItem]) -> list[str]:
        rendered_items = "\n".join(f"- {item.text}" for item in items)
        return [header, rendered_items]
