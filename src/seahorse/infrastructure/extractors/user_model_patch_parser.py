from __future__ import annotations

import json

from pydantic import ValidationError

from seahorse import logger
from seahorse.domain.models import UserModelPatch


class UserModelPatchParser:
    def parse(self, raw_output: str) -> UserModelPatch:
        normalized = raw_output.strip()
        if normalized.startswith("```"):
            normalized = self._strip_code_fence(normalized)

        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError as exc:
            logger.error("extractor.output.invalid_json", {}, exc=exc)
            raise RuntimeError("LLM extractor returned invalid JSON") from exc

        try:
            return UserModelPatch.model_validate(payload)
        except ValidationError as exc:
            logger.error("extractor.output.invalid_schema", {}, exc=exc)
            raise RuntimeError("LLM extractor returned an invalid patch payload") from exc

    def _strip_code_fence(self, content: str) -> str:
        lines = content.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return content
