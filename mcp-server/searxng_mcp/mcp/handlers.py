"""MCP tool call handlers (search, fetch, crawl, extract)."""

import json
from typing import Any, Dict, List

from mcp.types import TextContent

from searxng_mcp.client import client
from searxng_mcp.config import (
    DEFAULT_FETCH_CONTENT_LIMIT,
    DEFAULT_SEARCH_RESULTS_LIMIT,
    DEFAULT_SEARCH_SNIPPET_LIMIT,
    DEFAULT_SUBPAGE_LIMIT,
    ERROR_CRAWL_PREFIX,
    ERROR_EXTRACT_DISABLED,
    ERROR_FETCH_PREFIX,
    ERROR_QUERY_REQUIRED,
    ERROR_SEARCH_PREFIX,
    ERROR_URL_REQUIRED,
    EXTRACT_ENABLED,
    MAX_FETCH_CONTENT_LIMIT,
    MAX_SEARCH_RESULTS_LIMIT,
    MAX_SEARCH_SNIPPET_LIMIT,
    MAX_SUBPAGE_LIMIT,
    NO_RESULTS_FOUND,
)
from searxng_mcp.content_utils import truncate_content_with_links
from searxng_mcp.extract_service import run_extract_pipeline
from searxng_mcp.mcp.responses import create_error_response
from searxng_mcp.mcp.tools import parse_comma_separated


async def handle_search_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle search tool requests."""
    query = arguments.get("query")
    if not query:
        return create_error_response(ERROR_QUERY_REQUIRED)

    categories = parse_comma_separated(arguments.get("categories"))
    engines = parse_comma_separated(arguments.get("engines"))
    language = arguments.get("language", "en")
    time_range = arguments.get("time_range")
    pageno = arguments.get("pageno", 1)
    max_results = arguments.get("max_results", DEFAULT_SEARCH_RESULTS_LIMIT)

    if time_range and time_range not in ["day", "month", "year"]:
        return create_error_response("Error: time_range must be one of: day, month, year")

    max_results = min(max_results, MAX_SEARCH_RESULTS_LIMIT)
    pageno = max(1, pageno)

    results = client.search(query, categories, engines, language, time_range, pageno)

    if "error" in results:
        return create_error_response(ERROR_SEARCH_PREFIX.format(error=results["error"]))

    if "results" not in results or not results["results"]:
        return [TextContent(type="text", text=NO_RESULTS_FOUND)]

    formatted_results = []
    for i, result in enumerate(results["results"][:max_results], 1):
        title = result.get("title", "N/A")
        url = result.get("url", "N/A")
        content = result.get("content", "")
        engine = result.get("engine", "N/A")

        if content and DEFAULT_SEARCH_SNIPPET_LIMIT is not None and len(content) > DEFAULT_SEARCH_SNIPPET_LIMIT:
            content = content[:DEFAULT_SEARCH_SNIPPET_LIMIT] + "..."
        elif content and len(content) > MAX_SEARCH_SNIPPET_LIMIT:
            content = content[:MAX_SEARCH_SNIPPET_LIMIT] + "..."

        formatted_results.append(
            f"{i}. {title}\n   URL: {url}\n   Engine: {engine}\n   Content: {content}\n"
        )

    response = (
        f"Search results for '{query}' (showing {len(formatted_results)} of "
        f"{len(results['results'])} results):\n\n" + "\n".join(formatted_results)
    )
    return [TextContent(type="text", text=response)]


async def handle_fetch_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle fetch tool requests."""
    url = arguments.get("url")
    if not url:
        return create_error_response(ERROR_URL_REQUIRED)

    headers = arguments.get("headers")
    max_content_length = arguments.get("max_content_length", DEFAULT_FETCH_CONTENT_LIMIT)

    if max_content_length is not None:
        max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)

    result = client.fetch(url, headers)

    if "error" in result:
        return create_error_response(ERROR_FETCH_PREFIX.format(error=result["error"]))

    response = f"Fetched content from: {result['url']}\n"
    response += f"Status Code: {result['status_code']}\n"
    if "original_content_length" in result:
        response += f"Original Content Length: {result['original_content_length']} characters\n"
    response += f"Clean Text Length: {result['content_length']} characters\n\n"

    content = result["content"]
    if max_content_length is not None and len(content) > max_content_length:
        content = truncate_content_with_links(content, max_content_length)

    response += f"Clean Text Content:\n{content}"

    return [TextContent(type="text", text=response)]


async def handle_crawl_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle crawl tool requests."""
    url = arguments.get("url")
    if not url:
        return create_error_response(ERROR_URL_REQUIRED)

    filters = arguments.get("filters")
    headers = arguments.get("headers")
    subpage_limit = arguments.get("subpage_limit", DEFAULT_SUBPAGE_LIMIT)
    max_content_length = arguments.get("max_content_length", DEFAULT_FETCH_CONTENT_LIMIT)

    subpage_limit = min(subpage_limit, MAX_SUBPAGE_LIMIT)
    if max_content_length is not None:
        max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)

    result = client.crawl(url, filters, headers, subpage_limit, max_content_length)

    if "error" in result:
        return create_error_response(ERROR_CRAWL_PREFIX.format(error=result["error"]))

    response = f"Crawled: {result['main_page']['url']}\n"
    response += f"Main page content length: {result['main_page']['content_length']} characters\n"
    response += f"Total subpages found: {result['total_subpages_found']}\n"
    response += f"Subpages returned: {result['subpages_returned']}\n"

    if result["filters_applied"]:
        response += f"Filters applied: {', '.join(result['filters_applied'])}\n"

    response += "\n" + "=" * 50 + "\n"
    response += "MAIN PAGE CONTENT:\n"
    response += "=" * 50 + "\n"

    main_content = result["main_page"]["content"]
    if max_content_length is not None and len(main_content) > max_content_length:
        main_content = truncate_content_with_links(main_content, max_content_length)

    response += f"{main_content}\n\n"

    if result["subpages"]:
        response += "=" * 50 + "\n"
        response += "SUBPAGES:\n"
        response += "=" * 50 + "\n"

        for i, subpage in enumerate(result["subpages"], 1):
            response += f"\n{i}. {subpage['anchor_text']}\n"
            response += f"   URL: {subpage['url']}\n"
            response += f"   Content Length: {subpage['content_length']} characters\n"
            response += f"   Content: {subpage['content']}\n"
            response += "-" * 30 + "\n"

    return [TextContent(type="text", text=response)]


async def handle_extract_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    if not EXTRACT_ENABLED:
        return create_error_response(ERROR_EXTRACT_DISABLED)
    body, status = await run_extract_pipeline(arguments)
    if status >= 400:
        return create_error_response(str(body.get("error", "extract failed")))
    if body.get("error"):
        return create_error_response(str(body["error"]))
    return [TextContent(type="text", text=json.dumps(body, ensure_ascii=False))]
