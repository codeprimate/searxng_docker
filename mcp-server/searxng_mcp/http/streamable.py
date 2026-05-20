"""Streamable HTTP MCP transport wiring for the low-level MCP Server."""

from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from searxng_mcp.config import MCP_JSON_RESPONSE, MCP_STATELESS_HTTP
from searxng_mcp.mcp.app import app as mcp_server


def create_session_manager() -> StreamableHTTPSessionManager:
    """Build a session manager for the shared low-level MCP server instance."""
    return StreamableHTTPSessionManager(
        app=mcp_server,
        stateless=MCP_STATELESS_HTTP,
        json_response=MCP_JSON_RESPONSE,
    )


def streamable_asgi_app(session_manager: StreamableHTTPSessionManager) -> StreamableHTTPASGIApp:
    """ASGI app delegate for Streamable HTTP MCP requests."""
    return StreamableHTTPASGIApp(session_manager)
