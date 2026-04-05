from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from seahorse.bootstrap import AppContainer, build_app_container
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.recall_context import recall_context


class HTTPMessage(BaseModel):
    role: str
    text: str


class IngestRequest(BaseModel):
    session_id: str | None = None
    content: str | None = None
    messages: list[HTTPMessage] = Field(default_factory=list)


def create_http_app(container: AppContainer) -> FastAPI:
    app = FastAPI(title="Seahorse", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/memory/context")
    def get_memory_context() -> dict[str, str]:
        return recall_context(container.recall_service)

    @app.post("/memory/ingest")
    def post_memory_ingest(request: IngestRequest) -> dict[str, object]:
        return ingest_turn(
            container.ingest_service,
            content=request.content,
            messages=[message.model_dump() for message in request.messages],
            source="http",
            session_id=request.session_id,
        )

    return app


def build_default_http_app(project_root: Path) -> FastAPI:
    return create_http_app(build_app_container(project_root))
