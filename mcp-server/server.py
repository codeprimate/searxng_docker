#!/usr/bin/env python3
"""
SearXNG MCP Server - Self-contained MCP server for SearXNG search engine.

Entry point: stdio MCP or `--web` Starlette (REST mirror + streamable HTTP MCP).
"""

import asyncio
import os
import sys

from mcp.server.stdio import stdio_server

from searxng_mcp import __version__
from searxng_mcp.mcp.app import app

# Re-exports for tests and backward compatibility
from searxng_mcp.config import parse_env_bool  # noqa: F401
from searxng_mcp.mcp.tools import build_tool_definitions, tools_to_json_list  # noqa: F401


async def main_stdio() -> None:
    # stderr only: stdout is the MCP JSON-RPC transport in stdio mode.
    print(f"searxng-mcp {__version__} starting (stdio)", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def main_web() -> None:
    import uvicorn

    from searxng_mcp.http.routes import create_web_app

    port = int(os.environ.get("PORT", 7778))
    print(f"searxng-mcp {__version__} starting (web) on port {port}", file=sys.stderr)
    uvicorn.run(create_web_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--web":
        main_web()
    else:
        asyncio.run(main_stdio())
