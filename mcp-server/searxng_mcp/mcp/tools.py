"""MCP tool schemas and JSON serialization for the HTTP /tools endpoint."""

from typing import Any, Dict, List, Optional

from mcp.types import Tool

from searxng_mcp.config import (
    DEFAULT_SEARCH_RESULTS_LIMIT,
    DEFAULT_SUBPAGE_LIMIT,
    MAX_FETCH_CONTENT_LIMIT,
    MAX_SEARCH_RESULTS_LIMIT,
    MAX_SUBPAGE_LIMIT,
)

# Extract: MCP fetches the URL, sidecar returns JSON matching json_schema (subset).
EXTRACT_TOOL_DESCRIPTION = (
    "Fetch a URL (same HTML-stripped text as fetch) and return one JSON object that "
    "must satisfy json_schema. Required: url, json_schema. Optional: prompt (extraction "
    "rules not captured by the schema), headers (HTTP for the fetch). Prefer a flat "
    "output shape; the json_schema parameter documents the supported subset, null vs "
    "omission, and unsupported keywords."
)

EXTRACT_JSON_SCHEMA_PROPERTY_DESCRIPTION = (
    "JSON Schema subset for the single returned object. Put mandatory keys in "
    '"required"; keep the shape flat when possible. Keys outside "required" may be '
    'omitted. If a key might be JSON null (not only absent), union its "type" with '
    '"null" (e.g. ["string","null"], ["object","null"] with nested "properties"); '
    'otherwise null fails. Unsupported: the "nullable" keyword; additionalProperties: '
    'true. Use "prompt" for extraction rules the schema does not encode.'
)


def parse_comma_separated(value: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated string into list, return None if empty."""
    return value.split(",") if value else None


def build_tool_definitions(extract_enabled: bool) -> List[Tool]:
    """Single source of truth for MCP list_tools and HTTP /tools."""
    tools: List[Tool] = [
        Tool(
            name="search",
            description="Search using SearXNG metasearch engine",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "categories": {
                        "type": "string",
                        "description": "Comma-separated categories (general,it,videos,images)",
                    },
                    "engines": {
                        "type": "string",
                        "description": (
                            "Comma-separated engines (bing,duckduckgo,google,startpage,"
                            "wikipedia,github,reddit,youtube,stackexchange,etc.)"
                        ),
                    },
                    "language": {"type": "string", "description": "Language code (default: en)"},
                    "time_range": {
                        "type": "string",
                        "description": "Time range for search results (day, month, year)",
                    },
                    "pageno": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": (
                            f"Maximum number of results to return (default: "
                            f"{DEFAULT_SEARCH_RESULTS_LIMIT}, max: {MAX_SEARCH_RESULTS_LIMIT})"
                        ),
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="fetch",
            description="Fetch content from a URL and return clean text (HTML stripped)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch content from"},
                    "headers": {
                        "type": "object",
                        "description": "Optional custom headers as key-value pairs",
                    },
                    "max_content_length": {
                        "type": "integer",
                        "description": (
                            f"Maximum content length in characters (default: no limit, max: "
                            f"{MAX_FETCH_CONTENT_LIMIT})"
                        ),
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="crawl",
            description=(
                "Crawl a page and return its content plus up to subpage_limit subpages "
                "that match filter criteria"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to crawl"},
                    "filters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Array of strings to filter anchor text (at least one must match)"
                        ),
                    },
                    "headers": {
                        "type": "object",
                        "description": "Optional custom headers as key-value pairs",
                    },
                    "subpage_limit": {
                        "type": "integer",
                        "description": (
                            f"Maximum number of subpages to crawl (default: {DEFAULT_SUBPAGE_LIMIT}, "
                            f"max: {MAX_SUBPAGE_LIMIT})"
                        ),
                    },
                    "max_content_length": {
                        "type": "integer",
                        "description": (
                            f"Maximum content length per page in characters (default: no limit, max: "
                            f"{MAX_FETCH_CONTENT_LIMIT})"
                        ),
                    },
                },
                "required": ["url"],
            },
        ),
    ]
    if extract_enabled:
        tools.append(
            Tool(
                name="extract",
                description=EXTRACT_TOOL_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "HTTP(S) URL of the page to fetch and extract from (required)",
                        },
                        "json_schema": {
                            "type": "object",
                            "description": EXTRACT_JSON_SCHEMA_PROPERTY_DESCRIPTION,
                        },
                        "prompt": {
                            "type": "string",
                            "description": (
                                "Optional. Natural-language partner to json_schema: say what to extract "
                                "from the page, how to interpret edge cases, priorities, or formatting—"
                                "anything not captured by the schema alone. Omit when the schema fully "
                                "specifies the task. There is no required wording; you (the caller) "
                                "decide the task together with json_schema."
                            ),
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP request headers for fetching the URL",
                        },
                    },
                    "required": ["url", "json_schema"],
                },
            )
        )
    return tools


def tools_to_json_list(tools_list: List[Tool]) -> List[Dict[str, Any]]:
    return [
        {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
        for t in tools_list
    ]
