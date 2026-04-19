from __future__ import annotations

from dataclasses import dataclass

from seahorse.domain.models import FactItem, FactPatchItem, TextItem, UserProfile, UserProfilePatch


@dataclass(frozen=True)
class MergeResult:
    user_profile: UserProfile
    changed: bool


class UserProfileMerger:
    """Merge structured patches into the persisted user model."""

    _FACT_PREFIX = "fact"
    _PREFERENCE_PREFIX = "preference"
    _CONSTRAINT_PREFIX = "constraint"

    def merge(self, current: UserProfile | None, patch: UserProfilePatch) -> MergeResult:
        baseline = current or UserProfile()

        summary = patch.summary.strip() or baseline.summary
        facts = self._merge_facts(
            baseline.facts,
            patch.facts_to_add,
            patch.fact_ids_to_remove,
        )
        preferences = self._merge_text_items(
            baseline.preferences,
            patch.preferences_to_add,
            patch.preference_ids_to_remove,
            self._PREFERENCE_PREFIX,
        )
        constraints = self._merge_text_items(
            baseline.constraints,
            patch.constraints_to_add,
            patch.constraint_ids_to_remove,
            self._CONSTRAINT_PREFIX,
        )

        user_model = UserProfile(
            summary=summary,
            facts=facts,
            preferences=preferences,
            constraints=constraints,
        )
        changed = current is None and bool(summary or facts or preferences or constraints)
        if current is not None:
            changed = current != user_model

        if not changed:
            return MergeResult(user_profile=baseline, changed=False)
        return MergeResult(user_profile=user_model, changed=True)

    def _merge_facts(
        self,
        existing: list[FactItem],
        additions: list[FactPatchItem],
        removals: list[str],
    ) -> list[FactItem]:
        removal_ids = {item_id.strip() for item_id in removals if item_id.strip()}
        merged = [item.model_copy(deep=True) for item in existing if item.id not in removal_ids]

        active_pairs = {(item.category, item.text.strip()) for item in merged if item.text.strip()}
        next_index = self._next_item_index(merged, self._FACT_PREFIX)
        for addition in additions:
            text = addition.text.strip()
            pair = (addition.category, text)
            if not text or pair in active_pairs:
                continue
            merged.append(
                FactItem(
                    id=f"{self._FACT_PREFIX}_{next_index:03d}",
                    category=addition.category,
                    text=text,
                )
            )
            active_pairs.add(pair)
            next_index += 1
        return merged

    def _merge_text_items(
        self,
        existing: list[TextItem],
        additions: list[str],
        removals: list[str],
        prefix: str,
    ) -> list[TextItem]:
        removal_ids = {item_id.strip() for item_id in removals if item_id.strip()}
        merged = [item.model_copy(deep=True) for item in existing if item.id not in removal_ids]

        active_texts = {item.text.strip() for item in merged if item.text.strip()}
        next_index = self._next_item_index(merged, prefix)
        for raw_text in additions:
            text = raw_text.strip()
            if not text or text in active_texts:
                continue
            merged.append(TextItem(id=f"{prefix}_{next_index:03d}", text=text))
            active_texts.add(text)
            next_index += 1
        return merged

    def _next_item_index(self, items: list[FactItem] | list[TextItem], prefix: str) -> int:
        max_index = 0
        for item in items:
            index = self._parse_item_index(item.id, prefix)
            if index > max_index:
                max_index = index
        return max_index + 1

    def _parse_item_index(self, item_id: str, prefix: str) -> int:
        expected_prefix = f"{prefix}_"
        if not item_id.startswith(expected_prefix):
            return 0
        suffix = item_id[len(expected_prefix) :]
        return int(suffix) if suffix.isdigit() else 0
