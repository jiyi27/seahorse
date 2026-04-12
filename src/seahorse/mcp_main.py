import sys
from pathlib import Path

from seahorse.api.mcp_server import build_default_mcp_server


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    try:
        server = build_default_mcp_server(project_root)
    except Exception as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    server.run("stdio")
