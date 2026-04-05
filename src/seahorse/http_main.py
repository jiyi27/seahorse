from __future__ import annotations

from pathlib import Path

import uvicorn

from seahorse.api.http_server import build_default_http_app


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    app = build_default_http_app(project_root)
    uvicorn.run(app, host="127.0.0.1", port=8000)
