from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from seahorse import logger


def register_http_exception_handlers(app: FastAPI) -> None:
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
