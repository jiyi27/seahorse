.DEFAULT_GOAL := help

.PHONY: help sync test run run-mcp infra-init infra-up infra-down ollama-pull

help:
	@printf "Available targets:\n"
	@printf "  make sync      Install project dependencies with uv\n"
	@printf "  make test      Run the test suite\n"
	@printf "  make infra-init Start Qdrant and Ollama, pull nomic-embed-text, then sync deps\n"
	@printf "  make infra-up   Start Qdrant and Ollama containers\n"
	@printf "  make infra-down Stop Qdrant and Ollama containers\n"
	@printf "  make ollama-pull Pull the nomic-embed-text model into the Ollama container\n"
	@printf "  make run       Start the Seahorse HTTP server on 127.0.0.1:8081\n"
	@printf "  make run-mcp   Start the Seahorse MCP server over stdio\n"

sync:
	uv sync

test:
	uv run pytest

infra-init:
	docker compose up -d
	docker compose exec ollama ollama pull nomic-embed-text:latest
	uv sync

infra-up:
	docker compose up -d

infra-down:
	docker compose stop

ollama-pull:
	docker compose exec ollama ollama pull nomic-embed-text:latest

run:
	uv run seahorse-http

run-mcp:
	uv run seahorse-mcp
