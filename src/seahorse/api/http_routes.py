from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from seahorse.api.constants import (
    HEALTH_PATH,
    MEMORY_INGEST_PATH,
    MEMORY_SEARCH_PATH,
    USER_PROFILE_PATH,
)
from seahorse.bootstrap import SeahorseRuntime
from seahorse.domain.models import Message
from seahorse.tools.contracts import (
    GetUserProfileResult,
    IngestTurnResult,
    SearchMemoryResult,
    ToolFailure,
)
from seahorse.tools.get_user_profile import get_user_profile
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.search_memory import search_memory


class IngestRequest(BaseModel):
    session_id: str | None = None
    content: str | None = None
    messages: list[Message] = Field(default_factory=list)


def _error_response(payload: ToolFailure) -> JSONResponse:
    return JSONResponse(status_code=500, content=payload)


def _http_tool_response(
    payload: GetUserProfileResult | SearchMemoryResult | IngestTurnResult,
) -> JSONResponse:
    if payload["success"]:
        return JSONResponse(status_code=200, content=payload)
    return _error_response(payload)


def register_http_routes(app: FastAPI, runtime: SeahorseRuntime) -> None:
    @app.get(HEALTH_PATH)
    def health() -> dict[str, object]:
        return runtime.health_service.check()

    @app.get(USER_PROFILE_PATH)
    def get_user_profile_endpoint() -> JSONResponse:
        return _http_tool_response(get_user_profile(runtime.user_profile_service))

    @app.get(MEMORY_SEARCH_PATH)
    def get_memory_search(
        query: Annotated[str, Query(min_length=1)],
    ) -> JSONResponse:
        return _http_tool_response(
            search_memory(
                runtime.memory_search_service,
                query=query,
            )
        )

    @app.post(MEMORY_INGEST_PATH)
    def post_memory_ingest(request: IngestRequest) -> JSONResponse:
        return _http_tool_response(
            ingest_turn(
                runtime.session_ingest_service,
                content=request.content,
                messages=request.messages,
                source="http",
                session_id=request.session_id,
            )
        )
