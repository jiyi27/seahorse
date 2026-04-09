from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from seahorse.api.mcp_logging import wrap_mcp_tool
from seahorse.bootstrap import AppContainer
from seahorse.tools.contracts import (
    GetUserProfileResult,
    IngestTurnResult,
    SearchMemoryResult,
    ToolInputMessage,
)
from seahorse.tools.get_user_profile import get_user_profile
from seahorse.tools.ingest_turn import ingest_turn
from seahorse.tools.search_memory import search_memory
from seahorse.tools.tool_names import (
    GET_USER_PROFILE_TOOL,
    INGEST_TURN_TOOL,
    SEARCH_MEMORY_TOOL,
)


def register_mcp_tools(server: FastMCP, container: AppContainer) -> None:
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
        @wrap_mcp_tool(GET_USER_PROFILE_TOOL)
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
        @wrap_mcp_tool(SEARCH_MEMORY_TOOL)
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
        @wrap_mcp_tool(INGEST_TURN_TOOL)
        def ingest_turn_tool(
            content: str | None = None,
            messages: list[ToolInputMessage] | None = None,
            session_id: str | None = None,
        ) -> IngestTurnResult:
            return ingest_turn(
                container.session_ingest_service,
                content=content,
                messages=messages,
                source="mcp",
                session_id=session_id,
            )
