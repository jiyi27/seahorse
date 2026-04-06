from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from seahorse.bootstrap import AppContainer, build_app_container
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.recall_context import recall_context
from seahorse.tools.contracts import ToolInputMessage


def create_mcp_server(container: AppContainer) -> FastMCP:
    server = FastMCP(
        name="seahorse",
        instructions=(
            "Seahorse provides stable memory context and memory ingestion for an agent."
        ),
    )

    @server.tool(
        name="recall_context",
        description=(
            "Returns the user's persistent memory context, including behavioral "
            "rules and accumulated profile. Call at the start of every session "
            "before personalizing any response."
        ),
    )
    def recall_context_tool() -> dict[str, str | None]:
        return recall_context(container.recall_service, container.user_model_renderer)

    @server.tool(
        name="ingest_turn",
        description=(
            "Persists new stable facts, preferences, or constraints learned about "
            "the user into long-term memory. Call at the end of a session or after "
            "a significant exchange. Do not call for one-off requests that imply "
            "no durable preference."
        ),
    )
    def ingest_turn_tool(
        content: str | None = None,
        messages: list[ToolInputMessage] | None = None,
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
