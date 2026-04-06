from __future__ import annotations

from typing import Protocol

from seahorse.domain.models import Persona, UserModel


class PersonaRepository(Protocol):
    def load(self) -> Persona: ...


class UserModelRepository(Protocol):
    def load(self) -> UserModel | None: ...
    def save(self, model: UserModel) -> None: ...
