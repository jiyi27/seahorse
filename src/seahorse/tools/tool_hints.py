from __future__ import annotations

INGEST_RETRY_HINT = (
    "An internal error occurred. Retry up to 2 times; if still failing, stop and "
    "notify the user with the message above."
)
USER_PROFILE_SUCCESS_HINT = (
    "You now have the user's profile. Keep it in your current context. Do not "
    "call this tool again unless you no longer have this information in your "
    "current context."
)
USER_PROFILE_EMPTY_HINT = (
    "No user profile has been built yet. Proceed without personalization."
)
USER_PROFILE_UNAVAILABLE_HINT = (
    "User profile unavailable. Proceed without personalization. Do not halt."
)
SEARCH_MEMORY_HAS_RESULTS_HINT = (
    "These may or may not be what you're looking for - treat them as loose leads, "
    "not confirmed facts. If something looks relevant, bring it up naturally "
    "rather than announcing a search result. If you're unsure, ask casually. "
    "If two attempts don't land, let it go - tell the user you can't quite place "
    "it and move on."
)
SEARCH_MEMORY_NO_RESULTS_HINT = (
    "No matching memory was found for this query. Do not guess. You may tell the "
    "user you don't recall, or ask them directly what they are referring to."
)
SEARCH_MEMORY_FAILED_HINT = (
    "Memory search failed. Do not retry automatically. Proceed without recalled "
    "context."
)
