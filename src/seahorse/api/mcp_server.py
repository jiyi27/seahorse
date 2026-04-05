from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from seahorse.bootstrap import AppContainer, build_app_container
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.recall_context import recall_context


def create_mcp_server(container: AppContainer) -> FastMCP:
    server = FastMCP(
        name="seahorse",
        instructions=(
            "Seahorse provides stable memory context and memory ingestion for a single user."
        ),
    )

    @server.tool(
        name="recall_context",
        description="Load stable memory context including core rule and user model.",
    )
    def recall_context_tool() -> dict[str, str]:
        return recall_context(container.recall_service)

    @server.tool(
        name="ingest_turn",
        description="Ingest a conversation turn or summary to update the user model.",
    )
    def ingest_turn_tool(
        content: str | None = None,
        messages: list[dict[str, str]] | None = None,
        session_id: str | None = None,
    ) -> dict[str, object]:
        return ingest_turn(
            container.ingest_service,
            content=content,
            messages=messages,
            source="mcp",
            session_id=session_id,
        )

    return server


def build_default_mcp_server(project_root: Path) -> FastMCP:
    return create_mcp_server(build_app_container(project_root))
