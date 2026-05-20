"""Starlette REST API mirroring search/fetch/crawl/extract, health, and streamable MCP."""

import contextlib
import json
from collections.abc import AsyncIterator

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

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
    MCP_STREAMABLE_ENABLED,
    MCP_STREAMABLE_PATH,
)
from searxng_mcp.content_utils import truncate_content_with_links
from searxng_mcp.extract_service import run_extract_pipeline
from searxng_mcp.http.streamable import create_session_manager, streamable_asgi_app
from searxng_mcp.mcp.tools import build_tool_definitions, tools_to_json_list


async def search_endpoint(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        query = data.get("query")
        if not query:
            return JSONResponse({"error": "Query is required"}, status_code=400)

        categories = data.get("categories")
        engines = data.get("engines")
        language = data.get("language", "en")
        time_range = data.get("time_range")
        pageno = data.get("pageno", 1)
        max_results = data.get("max_results", DEFAULT_SEARCH_RESULTS_LIMIT)

        if time_range and time_range not in ["day", "month", "year"]:
            return JSONResponse(
                {"error": "time_range must be one of: day, month, year"},
                status_code=400,
            )

        categories_list = categories.split(",") if categories else None
        engines_list = engines.split(",") if engines else None

        max_results = min(max_results, MAX_SEARCH_RESULTS_LIMIT)
        pageno = max(1, pageno)

        results = client.search(
            query, categories_list, engines_list, language, time_range, pageno
        )

        if "results" in results and results["results"]:
            results["results"] = results["results"][:max_results]

        return JSONResponse(results)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def health_endpoint(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy"})


async def fetch_endpoint(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        url = data.get("url")
        if not url:
            return JSONResponse({"error": "URL is required"}, status_code=400)

        headers = data.get("headers")
        max_content_length = data.get("max_content_length", DEFAULT_FETCH_CONTENT_LIMIT)

        if max_content_length is not None:
            max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)

        result = client.fetch(url, headers)

        if (
            "content" in result
            and max_content_length is not None
            and len(result["content"]) > max_content_length
        ):
            result["content"] = truncate_content_with_links(
                result["content"], max_content_length
            )
            result["content_length"] = len(result["content"])

        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def crawl_endpoint(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        url = data.get("url")
        if not url:
            return JSONResponse({"error": "URL is required"}, status_code=400)

        filters = data.get("filters")
        headers = data.get("headers")
        subpage_limit = data.get("subpage_limit", DEFAULT_SUBPAGE_LIMIT)
        max_content_length = data.get("max_content_length", DEFAULT_FETCH_CONTENT_LIMIT)

        subpage_limit = min(subpage_limit, MAX_SUBPAGE_LIMIT)
        if max_content_length is not None:
            max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)

        result = client.crawl(url, filters, headers, subpage_limit, max_content_length)

        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def tools_endpoint(request: Request) -> JSONResponse:
    tools = tools_to_json_list(build_tool_definitions(EXTRACT_ENABLED))
    return JSONResponse({"tools": tools})


async def extract_endpoint(request: Request) -> JSONResponse:
    if not EXTRACT_ENABLED:
        return JSONResponse(
            {"error": ERROR_EXTRACT_HTTP_DISABLED, "code": CODE_EXTRACT_DISABLED},
            status_code=404,
        )
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > EXTRACT_MAX_JSON_BODY_BYTES:
                return JSONResponse(
                    {
                        "error": (
                            f"request body exceeds EXTRACT_MAX_JSON_BODY_BYTES "
                            f"({EXTRACT_MAX_JSON_BODY_BYTES})"
                        ),
                    },
                    status_code=413,
                )
        except ValueError:
            pass
    raw = await request.body()
    if len(raw) > EXTRACT_MAX_JSON_BODY_BYTES:
        return JSONResponse(
            {
                "error": (
                    f"request body exceeds EXTRACT_MAX_JSON_BODY_BYTES "
                    f"({EXTRACT_MAX_JSON_BODY_BYTES})"
                ),
            },
            status_code=413,
        )
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"error": "JSON body must be an object"}, status_code=400)
    body, status = await run_extract_pipeline(data)
    return JSONResponse(body, status_code=status)


def create_web_app() -> Starlette:
    """Starlette app: REST mirror routes and optional streamable MCP at MCP_STREAMABLE_PATH."""
    session_manager = create_session_manager() if MCP_STREAMABLE_ENABLED else None

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        if session_manager is not None:
            async with session_manager.run():
                yield
        else:
            yield

    routes = [
        Route("/search", search_endpoint, methods=["POST"]),
        Route("/fetch", fetch_endpoint, methods=["POST"]),
        Route("/crawl", crawl_endpoint, methods=["POST"]),
        Route("/extract", extract_endpoint, methods=["POST"]),
        Route("/health", health_endpoint, methods=["GET"]),
        Route("/tools", tools_endpoint, methods=["GET"]),
    ]

    if session_manager is not None:
        routes.append(
            Route(
                MCP_STREAMABLE_PATH,
                endpoint=streamable_asgi_app(session_manager),
            )
        )

    starlette_app = Starlette(routes=routes, lifespan=lifespan)

    if session_manager is not None:
        starlette_app = CORSMiddleware(
            starlette_app,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "DELETE"],
            expose_headers=["Mcp-Session-Id"],
        )

    return starlette_app
