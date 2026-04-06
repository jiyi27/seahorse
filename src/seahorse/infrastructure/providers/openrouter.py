from __future__ import annotations

from typing import Any

import httpx

from seahorse import logger
from seahorse.domain.models import ProviderSettings
from seahorse.infrastructure.providers.base import LLMProvider


class OpenRouterProvider(LLMProvider):
    def __init__(
        self,
        settings: ProviderSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        if settings.provider != "openrouter":
            msg = f"Unsupported provider for OpenRouterProvider: {settings.provider}"
            raise ValueError(msg)

        self._settings = settings
        self._http_client = http_client or httpx.Client(timeout=settings.timeout_seconds)

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        url = f"{self._settings.base_url.rstrip('/')}/chat/completions"
        logger.debug(
            "openrouter.request.started",
            {
                "model": self._settings.model,
                "url": url,
                "system_len": len(system_prompt),
                "user_len": len(user_prompt),
            },
        )
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        if self._settings.app_name:
            headers["X-Title"] = self._settings.app_name
        if self._settings.referer:
            headers["HTTP-Referer"] = self._settings.referer

        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
        }

        try:
            response = self._http_client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(
                "openrouter.request.http_error",
                {"model": self._settings.model, "url": url},
                exc=exc,
            )
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            logger.error(
                "openrouter.request.bad_json",
                {"model": self._settings.model},
                exc=exc,
            )
            raise RuntimeError("OpenRouter returned invalid JSON") from exc
        logger.debug(
            "openrouter.request.succeeded",
            {
                "model": self._settings.model,
                "response_len": len(response.text),
                "status_code": response.status_code,
            },
        )
        choices = body.get("choices") or []
        if not choices:
            logger.error(
                "openrouter.request.bad_schema",
                {
                    "model": self._settings.model,
                    "body_keys": sorted(body.keys()),
                },
            )
            raise RuntimeError("OpenRouter response did not include choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            text_chunks = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            merged = "".join(text_chunks).strip()
            if merged:
                return merged

        logger.error(
            "openrouter.request.no_content",
            {
                "model": self._settings.model,
                "content_type": type(content).__name__,
            },
        )
        raise RuntimeError("OpenRouter response did not include textual content")
