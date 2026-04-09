from __future__ import annotations

from typing import Protocol

from seahorse.domain.models import UserModel


class UserModelRepository(Protocol):
    def load(self) -> UserModel | None: ...
    def save(self, model: UserModel) -> None: ...
