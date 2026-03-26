"""MCP stdio server: tool list and dispatch."""

from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import TextContent, Tool

from searxng_mcp.config import ERROR_EXTRACT_DISABLED, ERROR_UNKNOWN_TOOL, EXTRACT_ENABLED
from searxng_mcp.mcp.handlers import (
    handle_crawl_tool,
    handle_extract_tool,
    handle_fetch_tool,
    handle_search_tool,
)
from searxng_mcp.mcp.responses import create_error_response
from searxng_mcp.mcp.tools import build_tool_definitions

app = Server("searxng-mcp")


@app.list_tools()
async def list_tools() -> List[Tool]:
    return build_tool_definitions(EXTRACT_ENABLED)


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch tool calls to appropriate handlers."""
    if name == "extract" and not EXTRACT_ENABLED:
        return create_error_response(ERROR_EXTRACT_DISABLED)

    tool_handlers = {
        "search": handle_search_tool,
        "fetch": handle_fetch_tool,
        "crawl": handle_crawl_tool,
    }
    if EXTRACT_ENABLED:
        tool_handlers["extract"] = handle_extract_tool

    handler = tool_handlers.get(name)
    if handler:
        return await handler(arguments)

    return create_error_response(ERROR_UNKNOWN_TOOL.format(name=name))
