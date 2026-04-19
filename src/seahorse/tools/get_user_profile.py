from __future__ import annotations

from seahorse.domain.models import UserProfile
from seahorse.domain.repositories import UserProfileRepository
from seahorse.tools.contracts import (
    GetUserProfileResult,
    GetUserProfileSuccess,
    UserProfilePayload,
    internal_error,
)
from seahorse.tools.tool_hints import (
    USER_PROFILE_EMPTY_HINT,
    USER_PROFILE_SUCCESS_HINT,
    USER_PROFILE_UNAVAILABLE_HINT,
)


def get_user_profile(user_profile_repository: UserProfileRepository) -> GetUserProfileResult:
    try:
        user_model = user_profile_repository.load()
    except RuntimeError as exc:
        return internal_error(str(exc), USER_PROFILE_UNAVAILABLE_HINT)

    if user_model is None:
        payload: GetUserProfileSuccess = {
            "success": True,
            "profile": None,
            "hint": USER_PROFILE_EMPTY_HINT,
        }
        return payload

    payload: GetUserProfileSuccess = {
        "success": True,
        "profile": _serialize_user_profile(user_model),
        "hint": USER_PROFILE_SUCCESS_HINT,
    }
    return payload


def _serialize_user_profile(user_profile: UserProfile) -> UserProfilePayload:
    return {
        "summary": user_profile.summary,
        "facts": [
            {
                "id": fact.id,
                "category": fact.category,
                "text": fact.text,
            }
            for fact in user_profile.facts
        ],
        "preferences": [
            {
                "id": preference.id,
                "text": preference.text,
            }
            for preference in user_profile.preferences
        ],
        "constraints": [
            {
                "id": constraint.id,
                "text": constraint.text,
            }
            for constraint in user_profile.constraints
        ],
    }
