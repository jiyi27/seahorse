from __future__ import annotations

from seahorse.application.recall_service import RecallService
from seahorse.domain.models import UserModel
from seahorse.tools.contracts import (
    GetUserProfileResult,
    GetUserProfileSuccess,
    USER_PROFILE_EMPTY_HINT,
    USER_PROFILE_UNAVAILABLE_HINT,
    UserProfilePayload,
    internal_error,
)


def get_user_profile(service: RecallService) -> GetUserProfileResult:
    try:
        user_model = service.get_user_model()
    except RuntimeError as exc:
        return internal_error(str(exc), USER_PROFILE_UNAVAILABLE_HINT)

    if user_model is None:
        payload: GetUserProfileSuccess = {
            "success": True,
            "profile": None,
            "hint": USER_PROFILE_EMPTY_HINT,
        }
        return payload

    payload = {
        "success": True,
        "profile": _serialize_user_model(user_model),
    }
    return payload


def _serialize_user_model(user_model: UserModel) -> UserProfilePayload:
    return {
        "summary": user_model.summary,
        "facts": [
            {
                "id": fact.id,
                "category": fact.category,
                "text": fact.text,
            }
            for fact in user_model.facts
        ],
        "preferences": [
            {
                "id": preference.id,
                "text": preference.text,
            }
            for preference in user_model.preferences
        ],
        "constraints": [
            {
                "id": constraint.id,
                "text": constraint.text,
            }
            for constraint in user_model.constraints
        ],
    }
