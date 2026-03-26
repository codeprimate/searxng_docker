#!/usr/bin/env python3
"""
SearXNG MCP Server - Self-contained MCP server for SearXNG search engine.

Entry point: stdio MCP or `--web` aiohttp REST API.
"""

import asyncio
import os
import sys

from aiohttp import web
from mcp.server.stdio import stdio_server

from searxng_mcp.mcp.app import app

# Re-exports for tests and backward compatibility
from searxng_mcp.config import parse_env_bool  # noqa: F401
from searxng_mcp.mcp.tools import build_tool_definitions, tools_to_json_list  # noqa: F401


async def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--web":
        from searxng_mcp.http.routes import create_web_app

        app_web = await create_web_app()
        port = int(os.environ.get("PORT", 7778))
        runner = web.AppRunner(app_web)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"Web server running on port {port}")
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            pass
    else:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )


if __name__ == "__main__":
    asyncio.run(main())
