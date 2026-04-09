from __future__ import annotations

import json
import uuid
from time import perf_counter

from fastapi import FastAPI, Request
from starlette.responses import Response

from seahorse import logger


def _decode_http_body(body: bytes) -> object:
    if not body:
        return None

    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text


async def _read_response_body(response: Response) -> tuple[bytes, Response]:
    body = getattr(response, "body", None)
    if isinstance(body, bytes) and body:
        return body, response

    body_iterator = getattr(response, "body_iterator", None)
    if body_iterator is None:
        return b"", response

    chunks = [chunk async for chunk in body_iterator]
    rendered_body = b"".join(chunks)
    rebuilt_response = Response(
        content=rendered_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
        background=response.background,
    )
    return rendered_body, rebuilt_response


def register_http_logging_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def attach_context_id(request: Request, call_next):
        context_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())[:8]
        logger.set_context_id(context_id)
        started_at = perf_counter()
        try:
            request_body = await request.body()
            logger.info(
                "http.request.received",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
                    "body": _decode_http_body(request_body),
                },
            )
            response = await call_next(request)
            response_body, response = await _read_response_body(response)
            response.headers["X-Request-Id"] = context_id
            logger.info(
                "http.response.completed",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                    "body": _decode_http_body(response_body),
                },
            )
            return response
        finally:
            logger.clear_context_id()
