from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from seahorse.api.http_errors import register_http_exception_handlers
from seahorse.api.http_logging import register_http_logging_middleware
from seahorse.api.http_routes import register_http_routes
from seahorse.bootstrap import SeahorseRuntime, build_runtime
from seahorse.constants import APP_NAME


def create_http_app(runtime: SeahorseRuntime) -> FastAPI:
    app = FastAPI(title=APP_NAME, version="0.1.0")
    register_http_logging_middleware(app)
    register_http_exception_handlers(app)
    register_http_routes(app, runtime)
    return app


def build_default_http_app(project_root: Path) -> FastAPI:
    return create_http_app(build_runtime(project_root))
