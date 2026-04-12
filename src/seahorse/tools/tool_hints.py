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
def search_memory_has_results_hint(count: int) -> str:
    return (
        f"Found {count} past conversation(s) from memory. Judge relevance yourself: "
        f"use what fits, ignore what clearly doesn't. If results seem off, retry "
        f"once — either rephrase the query or switch to the other language (Chinese "
        f"or English), as memory may have been stored in a different language. "
        f"After two attempts, tell the user you don't recall and move on — do not guess."
    )


SEARCH_MEMORY_NO_RESULTS_HINT = (
    "No conversation blocks matched your query in vector memory. Retry once — "
    "either rephrase the query or switch to the other language (Chinese or English), "
    "as memory may have been stored in a different language. If still nothing, tell "
    "the user you don't recall — do not guess or invent context."
)
SEARCH_MEMORY_FAILED_HINT = (
    "Memory search failed. Do not retry automatically. Proceed without recalled "
    "context."
)
