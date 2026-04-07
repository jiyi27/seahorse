from __future__ import annotations

from pathlib import Path
import uuid
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from seahorse import logger
from seahorse.api.constants import (
    HEALTH_PATH,
    MEMORY_INGEST_PATH,
    MEMORY_SEARCH_PATH,
    PERSONA_PATH,
    USER_PROFILE_PATH,
)
from seahorse.bootstrap import AppContainer, build_app_container
from seahorse.constants import APP_NAME
from seahorse.domain.models import Message
from seahorse.tools.contracts import (
    GetPersonaResult,
    GetUserProfileResult,
    IngestTurnResult,
    SearchMemoryResult,
    ToolFailure,
)
from seahorse.tools.get_persona import get_persona
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
    payload: GetPersonaResult | GetUserProfileResult | SearchMemoryResult | IngestTurnResult,
) -> JSONResponse:
    if payload["success"]:
        return JSONResponse(status_code=200, content=payload)
    return _error_response(payload)


def create_http_app(container: AppContainer) -> FastAPI:
    app = FastAPI(title=APP_NAME, version="0.1.0")

    @app.middleware("http")
    async def attach_context_id(request: Request, call_next):
        context_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())[:8]
        logger.set_context_id(context_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = context_id
            return response
        finally:
            logger.clear_context_id()

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.error(
            "http.validation_error",
            {"path": request.url.path, "method": request.method},
            exc=exc,
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Invalid request payload", "type": type(exc).__name__},
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.error(
            "http.validation_error",
            {"path": request.url.path, "method": request.method},
            exc=exc,
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Invalid request payload", "type": type(exc).__name__},
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(
        request: Request, exc: RuntimeError
    ) -> JSONResponse:
        logger.error(
            "http.runtime_error",
            {"path": request.url.path, "method": request.method},
            exc=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "type": type(exc).__name__},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "http.unhandled_error",
            {"path": request.url.path, "method": request.method},
            exc=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "type": type(exc).__name__},
        )

    @app.get(HEALTH_PATH)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(PERSONA_PATH)
    def get_persona_endpoint() -> JSONResponse:
        return _http_tool_response(get_persona(container.recall_service))

    @app.get(USER_PROFILE_PATH)
    def get_user_profile_endpoint() -> JSONResponse:
        return _http_tool_response(get_user_profile(container.recall_service))

    @app.get(MEMORY_SEARCH_PATH)
    def get_memory_search(
        query: Annotated[str, Query(min_length=1)],
        top_k: Annotated[int, Query(ge=1, le=10)] = 3,
    ) -> JSONResponse:
        return _http_tool_response(
            search_memory(
                container.memory_search_service,
                query=query,
                top_k=top_k,
            )
        )

    @app.post(MEMORY_INGEST_PATH)
    def post_memory_ingest(request: IngestRequest) -> JSONResponse:
        return _http_tool_response(
            ingest_turn(
                container.ingest_service,
                content=request.content,
                messages=request.messages,
                source="http",
                session_id=request.session_id,
            )
        )

    return app


def build_default_http_app(project_root: Path) -> FastAPI:
    return create_http_app(build_app_container(project_root))
