from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from seahorse.api.mcp_logging import wrap_mcp_tool
from seahorse.bootstrap import SeahorseRuntime
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


def register_mcp_tools(server: FastMCP, runtime: SeahorseRuntime) -> None:
    if GET_USER_PROFILE_TOOL in runtime.enabled_mcp_tools:
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
            return get_user_profile(runtime.user_profile_repository)

    if SEARCH_MEMORY_TOOL in runtime.enabled_mcp_tools:
        @server.tool(
            name=SEARCH_MEMORY_TOOL,
            description=(
                "Searches past conversation memory using vector similarity — your query "
                "is embedded and matched against stored conversation chunks by semantic "
                "distance. Write the query as a short declarative phrase that resembles "
                "what a stored memory might say — e.g. 'prefers dark mode' or "
                "'learning Rust at work' — not as a question like 'what does the user "
                "prefer?'. Retry with a rephrased query if needed, but attempt at most twice."
            ),
        )
        @wrap_mcp_tool(SEARCH_MEMORY_TOOL)
        def search_memory_tool(
            query: Annotated[str, "Short natural-language recall query"],
        ) -> SearchMemoryResult:
            return search_memory(
                runtime.memory_search_service,
                query=query,
            )

    if INGEST_TURN_TOOL in runtime.enabled_mcp_tools:
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
                runtime.session_ingest_service,
                content=content,
                messages=messages,
                session_id=session_id,
            )
