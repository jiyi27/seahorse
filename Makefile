.DEFAULT_GOAL := help

.PHONY: help sync test run run-mcp

help:
	@printf "Available targets:\n"
	@printf "  make sync      Install project dependencies with uv\n"
	@printf "  make test      Run the test suite\n"
	@printf "  make run       Start the Seahorse HTTP server on 127.0.0.1:8081\n"
	@printf "  make run-mcp   Start the Seahorse MCP server over stdio\n"

sync:
	uv sync

test:
	uv run pytest

run:
	uv run seahorse-http

run-mcp:
	uv run seahorse-mcp
