from __future__ import annotations

from seahorse.domain.models import ProviderSettings
from seahorse.infrastructure.providers.base import LLMProvider
from seahorse.infrastructure.providers.openrouter import OpenRouterProvider


def build_llm_provider(settings: ProviderSettings) -> LLMProvider:
    if settings.provider == "openrouter":
        return OpenRouterProvider(settings)

    raise ValueError(f"Unsupported provider: {settings.provider}")
