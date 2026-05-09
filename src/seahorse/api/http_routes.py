from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from seahorse.api.constants import (
    HEALTH_PATH,
    MEMORY_INGEST_PATH,
)
from seahorse.bootstrap import SeahorseRuntime
from seahorse.domain.models import Message
from seahorse.tools.contracts import (
    IngestTurnResult,
    ToolFailure,
)
from seahorse.tools.ingest_turn import ingest_turn


class IngestRequest(BaseModel):
    # 注入记忆时, 接口支持两种方式, 传递历史聊天记录或者传递一段文字描述 (不可同时传递)
    # 文字描述在 ingest 阶段会被包装成单条信息的 list[Message], role 是 user
    content: str | None = None
    messages: list[Message] = Field(default_factory=list)


def _error_response(payload: ToolFailure) -> JSONResponse:
    return JSONResponse(status_code=500, content=payload)


def _http_tool_response(
    payload: IngestTurnResult,
) -> JSONResponse:
    if payload["success"]:
        return JSONResponse(status_code=200, content=payload)
    return _error_response(payload)


def register_http_routes(app: FastAPI, runtime: SeahorseRuntime) -> None:
    @app.get(HEALTH_PATH)
    def health() -> dict[str, object]:
        return runtime.health_service.check()

    @app.post(MEMORY_INGEST_PATH)
    def post_memory_ingest(request: IngestRequest) -> JSONResponse:
        return _http_tool_response(
            ingest_turn(
                runtime.session_ingest_service,
                content=request.content,
                messages=request.messages,
            )
        )
