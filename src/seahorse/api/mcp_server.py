from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from seahorse.api.mcp_tools import register_mcp_tools
from seahorse.bootstrap import AppContainer, build_app_container


def create_mcp_server(container: AppContainer) -> FastMCP:
    server = FastMCP(
        name="seahorse",
        instructions=(
            "Seahorse provides stable memory context and memory ingestion for an agent."
        ),
    )
    register_mcp_tools(server, container)
    return server


def build_default_mcp_server(project_root: Path) -> FastMCP:
    return create_mcp_server(build_app_container(project_root))
