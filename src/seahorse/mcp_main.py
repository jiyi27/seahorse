from pathlib import Path

from seahorse.api.mcp_server import build_default_mcp_server


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    server = build_default_mcp_server(project_root)
    server.run("stdio")
