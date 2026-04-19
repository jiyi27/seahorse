from __future__ import annotations

from typing import Protocol

from seahorse.domain.models import UserProfile


class UserProfileRepository(Protocol):
    def load(self) -> UserProfile | None: ...
    def save(self, model: UserProfile) -> None: ...
