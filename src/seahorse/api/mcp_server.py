from __future__ import annotations

from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from seahorse.bootstrap import AppContainer, build_app_container
from seahorse.tools.contracts import (
    GetPersonaResult,
    GetUserProfileResult,
    IngestTurnResult,
    SearchMemoryResult,
    ToolInputMessage,
)
from seahorse.tools.get_persona import get_persona
from seahorse.tools.get_user_profile import get_user_profile
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.search_memory import search_memory
from seahorse.tools.tool_names import (
    GET_PERSONA_TOOL,
    GET_USER_PROFILE_TOOL,
    INGEST_TURN_TOOL,
    SEARCH_MEMORY_TOOL,
)


def create_mcp_server(container: AppContainer) -> FastMCP:
    server = FastMCP(
        name="seahorse",
        instructions=(
            "Seahorse provides stable memory context and memory ingestion for an agent."
        ),
    )

    if GET_PERSONA_TOOL in container.enabled_mcp_tools:
        @server.tool(
            name=GET_PERSONA_TOOL,
            description=(
                "Returns your persona - who you are, how you speak, and what you "
                "value. Call only if you do not already have this in your current "
                "context."
            ),
        )
        def get_persona_tool() -> GetPersonaResult:
            return get_persona(container.recall_service)

    if GET_USER_PROFILE_TOOL in container.enabled_mcp_tools:
        @server.tool(
            name=GET_USER_PROFILE_TOOL,
            description=(
                "Returns what is known about the user: their background, preferences, "
                "and constraints. Call only if you do not already have this in your "
                "current context. For retrieving specific past events or details, "
                f"use {SEARCH_MEMORY_TOOL} instead."
            ),
        )
        def get_user_profile_tool() -> GetUserProfileResult:
            return get_user_profile(container.recall_service)

    if SEARCH_MEMORY_TOOL in container.enabled_mcp_tools:
        @server.tool(
            name=SEARCH_MEMORY_TOOL,
            description=(
                "Searches past memory for context that might be relevant to what the "
                "user just said. Provide a short natural-language query describing "
                "what you're trying to recall. Returns a small configured set of "
                "results - treat them as leads, not confirmed facts."
            ),
        )
        def search_memory_tool(
            query: Annotated[str, "Short natural-language recall query"],
        ) -> SearchMemoryResult:
            return search_memory(
                container.memory_search_service,
                query=query,
            )

    if INGEST_TURN_TOOL in container.enabled_mcp_tools:
        @server.tool(
            name=INGEST_TURN_TOOL,
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
        ) -> IngestTurnResult:
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
