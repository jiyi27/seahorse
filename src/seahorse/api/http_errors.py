from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from seahorse import logger
from seahorse.api.constants import REQUEST_ID_HEADER


_INVALID_REQUEST_MESSAGE = "Invalid request payload"
_INTERNAL_SERVER_ERROR_MESSAGE = "Internal server error"


def _request_context(request: Request) -> dict[str, str]:
    return {
        "path": request.url.path,
        "method": request.method,
    }


def _response_with_request_id(
    *,
    status_code: int,
    content: dict[str, str],
    request: Request,
) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=content)
    request_id = request.headers.get(REQUEST_ID_HEADER) or logger.get_context_id()
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


def build_http_exception_response(
    request: Request,
    exc: Exception,
    *,
    log_exception: bool = True,
) -> JSONResponse:
    if isinstance(exc, (RequestValidationError, ValidationError)):
        topic = "http.validation_error"
        status_code = 422
        content = {
            "error": _INVALID_REQUEST_MESSAGE,
            "type": type(exc).__name__,
        }
    else:
        topic = "http.unhandled_error"
        status_code = 500
        content = {
            "error": _INTERNAL_SERVER_ERROR_MESSAGE,
            "type": type(exc).__name__,
        }

    if log_exception:
        logger.error(topic, _request_context(request), exc=exc)

    return _response_with_request_id(
        status_code=status_code,
        content=content,
        request=request,
    )


def register_http_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return build_http_exception_response(request, exc)

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return build_http_exception_response(request, exc)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return build_http_exception_response(request, exc)
