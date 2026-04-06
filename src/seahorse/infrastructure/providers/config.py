from __future__ import annotations

from seahorse.constants import APP_NAME, OPENROUTER_BASE_URL, OPENROUTER_PROVIDER
from seahorse.domain.models import ProviderSettings
from seahorse.infrastructure.config import ProviderConfig, SecretSettings


def validate_provider_config(
    provider_config: ProviderConfig, secrets: SecretSettings
) -> None:
    if provider_config.name == OPENROUTER_PROVIDER:
        if not provider_config.model:
            raise RuntimeError(
                "provider.model is required when provider.name is 'openrouter'"
            )
        if not secrets.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is required when provider.name is 'openrouter'"
            )
        return

    raise RuntimeError(f"Unsupported provider: {provider_config.name}")


def build_provider_settings(
    provider_config: ProviderConfig, secrets: SecretSettings
) -> ProviderSettings:
    validate_provider_config(provider_config, secrets)

    if provider_config.name == OPENROUTER_PROVIDER:
        return ProviderSettings(
            provider=OPENROUTER_PROVIDER,
            model=provider_config.model or "",
            api_key=secrets.openrouter_api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout_seconds=provider_config.timeout_seconds,
            app_name=APP_NAME,
            referer=None,
        )

    raise RuntimeError(f"Unsupported provider: {provider_config.name}")
