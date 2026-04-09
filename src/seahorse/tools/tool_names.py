from __future__ import annotations

GET_USER_PROFILE_TOOL = "get_user_profile"
SEARCH_MEMORY_TOOL = "search_memory"
INGEST_TURN_TOOL = "ingest_turn"

ALL_TOOL_NAMES = frozenset(
    {
        GET_USER_PROFILE_TOOL,
        SEARCH_MEMORY_TOOL,
        INGEST_TURN_TOOL,
    }
)
