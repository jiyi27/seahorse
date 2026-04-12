from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

from seahorse.api.http_server import build_default_http_app

_UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "uvicorn": {"handlers": [], "level": "CRITICAL", "propagate": False},
        "uvicorn.error": {"handlers": [], "level": "CRITICAL", "propagate": False},
        "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
    },
}


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    try:
        app = build_default_http_app(project_root)
    except Exception as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8081,
        access_log=False,
        log_config=_UVICORN_LOG_CONFIG,
    )
