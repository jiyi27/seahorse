from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable

from seahorse import logger


def wrap_mcp_tool(tool_name: str) -> Callable[[Callable], Callable]:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info("mcp.request.in", {"tool": tool_name, "args": kwargs})
            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:
                logger.error(
                    "mcp.request.failed", {"tool": tool_name, "args": kwargs}, exc=exc
                )
                raise
            logger.info("mcp.response.out", {"tool": tool_name, "result": result})
            return result

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info("mcp.request.in", {"tool": tool_name, "args": kwargs})
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                logger.error(
                    "mcp.request.failed", {"tool": tool_name, "args": kwargs}, exc=exc
                )
                raise
            logger.info("mcp.response.out", {"tool": tool_name, "result": result})
            return result

        return async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper

    return decorator
