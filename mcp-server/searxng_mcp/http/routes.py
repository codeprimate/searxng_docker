"""aiohttp REST API mirroring search/fetch/crawl/extract and health."""

import json

from aiohttp import web, web_request

from searxng_mcp.client import client
from searxng_mcp.config import (
    CODE_EXTRACT_DISABLED,
    DEFAULT_FETCH_CONTENT_LIMIT,
    DEFAULT_SEARCH_RESULTS_LIMIT,
    DEFAULT_SUBPAGE_LIMIT,
    ERROR_EXTRACT_HTTP_DISABLED,
    EXTRACT_ENABLED,
    EXTRACT_MAX_JSON_BODY_BYTES,
    MAX_FETCH_CONTENT_LIMIT,
    MAX_SEARCH_RESULTS_LIMIT,
    MAX_SUBPAGE_LIMIT,
)
from searxng_mcp.content_utils import truncate_content_with_links
from searxng_mcp.extract_service import run_extract_pipeline
from searxng_mcp.mcp.tools import build_tool_definitions, tools_to_json_list


async def search_endpoint(request: web_request.Request) -> web.Response:
    try:
        data = await request.json()
        query = data.get("query")
        if not query:
            return web.json_response({"error": "Query is required"}, status=400)

        categories = data.get("categories")
        engines = data.get("engines")
        language = data.get("language", "en")
        time_range = data.get("time_range")
        pageno = data.get("pageno", 1)
        max_results = data.get("max_results", DEFAULT_SEARCH_RESULTS_LIMIT)

        if time_range and time_range not in ["day", "month", "year"]:
            return web.json_response(
                {"error": "time_range must be one of: day, month, year"}, status=400
            )

        categories_list = categories.split(",") if categories else None
        engines_list = engines.split(",") if engines else None

        max_results = min(max_results, MAX_SEARCH_RESULTS_LIMIT)
        pageno = max(1, pageno)

        results = client.search(query, categories_list, engines_list, language, time_range, pageno)

        if "results" in results and results["results"]:
            results["results"] = results["results"][:max_results]

        return web.json_response(results)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def health_endpoint(request: web_request.Request) -> web.Response:
    return web.json_response({"status": "healthy"})


async def fetch_endpoint(request: web_request.Request) -> web.Response:
    try:
        data = await request.json()
        url = data.get("url")
        if not url:
            return web.json_response({"error": "URL is required"}, status=400)

        headers = data.get("headers")
        max_content_length = data.get("max_content_length", DEFAULT_FETCH_CONTENT_LIMIT)

        if max_content_length is not None:
            max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)

        result = client.fetch(url, headers)

        if "content" in result and max_content_length is not None and len(result["content"]) > max_content_length:
            result["content"] = truncate_content_with_links(result["content"], max_content_length)
            result["content_length"] = len(result["content"])

        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def crawl_endpoint(request: web_request.Request) -> web.Response:
    try:
        data = await request.json()
        url = data.get("url")
        if not url:
            return web.json_response({"error": "URL is required"}, status=400)

        filters = data.get("filters")
        headers = data.get("headers")
        subpage_limit = data.get("subpage_limit", DEFAULT_SUBPAGE_LIMIT)
        max_content_length = data.get("max_content_length", DEFAULT_FETCH_CONTENT_LIMIT)

        subpage_limit = min(subpage_limit, MAX_SUBPAGE_LIMIT)
        if max_content_length is not None:
            max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)

        result = client.crawl(url, filters, headers, subpage_limit, max_content_length)

        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def tools_endpoint(request: web_request.Request) -> web.Response:
    tools = tools_to_json_list(build_tool_definitions(EXTRACT_ENABLED))
    return web.json_response({"tools": tools})


async def extract_endpoint(request: web_request.Request) -> web.Response:
    if not EXTRACT_ENABLED:
        return web.json_response(
            {"error": ERROR_EXTRACT_HTTP_DISABLED, "code": CODE_EXTRACT_DISABLED},
            status=404,
        )
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > EXTRACT_MAX_JSON_BODY_BYTES:
                return web.json_response(
                    {
                        "error": (
                            f"request body exceeds EXTRACT_MAX_JSON_BODY_BYTES "
                            f"({EXTRACT_MAX_JSON_BODY_BYTES})"
                        ),
                    },
                    status=413,
                )
        except ValueError:
            pass
    raw = await request.read()
    if len(raw) > EXTRACT_MAX_JSON_BODY_BYTES:
        return web.json_response(
            {
                "error": (
                    f"request body exceeds EXTRACT_MAX_JSON_BODY_BYTES "
                    f"({EXTRACT_MAX_JSON_BODY_BYTES})"
                ),
            },
            status=413,
        )
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)
    if not isinstance(data, dict):
        return web.json_response({"error": "JSON body must be an object"}, status=400)
    body, status = await run_extract_pipeline(data)
    return web.json_response(body, status=status)


async def create_web_app() -> web.Application:
    app_web = web.Application()
    app_web.router.add_post("/search", search_endpoint)
    app_web.router.add_post("/fetch", fetch_endpoint)
    app_web.router.add_post("/crawl", crawl_endpoint)
    app_web.router.add_post("/extract", extract_endpoint)
    app_web.router.add_get("/health", health_endpoint)
    app_web.router.add_get("/tools", tools_endpoint)
    return app_web
