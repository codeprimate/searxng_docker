"""MCP text response helpers."""

from typing import List

from mcp.types import TextContent


def create_error_response(message: str) -> List[TextContent]:
    """Create a standardized error response."""
    return [TextContent(type="text", text=message)]
