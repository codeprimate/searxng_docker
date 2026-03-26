"""Extractor sidecar HTTP client and fetch→extract pipeline."""

import asyncio
import json
from typing import Any, Dict, Tuple

import aiohttp

from searxng_mcp.client import client
from searxng_mcp.config import (
    DEFAULT_FETCH_CONTENT_LIMIT,
    ERROR_EXTRACT_CONTENT_EMPTY,
    ERROR_EXTRACT_CONTENT_TOO_LONG,
    ERROR_EXTRACT_JSON_SCHEMA_REQUIRED,
    ERROR_EXTRACT_JSON_SCHEMA_TYPE,
    ERROR_EXTRACT_SIDECAR_URL,
    ERROR_FETCH_PREFIX,
    ERROR_URL_REQUIRED,
    EXTRACT_MAX_LENGTH,
    EXTRACT_SIDECAR_CONTENT_FORMAT,
    EXTRACT_TIMEOUT_SECONDS,
    EXTRACTOR_SIDECAR_URL,
    MAX_FETCH_CONTENT_LIMIT,
)
from searxng_mcp.content_utils import truncate_content_with_links


async def post_sidecar_extract(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """POST JSON to extractor sidecar. Returns (response_body, http_status)."""
    if not EXTRACTOR_SIDECAR_URL:
        return {"error": ERROR_EXTRACT_SIDECAR_URL}, 503
    url = f"{EXTRACTOR_SIDECAR_URL.rstrip('/')}/extract"
    timeout = aiohttp.ClientTimeout(total=float(EXTRACT_TIMEOUT_SECONDS))
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                text = await resp.text()
                try:
                    body = json.loads(text) if text else {}
                except json.JSONDecodeError:
                    return {"error": f"sidecar returned non-JSON ({resp.status})"}, 502
                if resp.status >= 400:
                    err = body.get("error", text) if isinstance(body, dict) else text
                    return {"error": str(err)}, resp.status
                if not isinstance(body, dict):
                    return {"error": "sidecar returned invalid JSON shape"}, 502
                return body, 200
    except asyncio.TimeoutError:
        return {"error": "sidecar request timed out (EXTRACT_TIMEOUT)"}, 502
    except aiohttp.ClientError as e:
        return {"error": f"sidecar unreachable: {e}"}, 502


async def run_extract_pipeline(arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Fetch URL, apply length limits, POST to sidecar.
    Returns (response_body, http_status). Fetch failures use HTTP 200 with error in body (same idea as /fetch).
    """
    url = arguments.get("url")
    json_schema = arguments.get("json_schema")
    if not url:
        return {"error": ERROR_URL_REQUIRED}, 400
    if json_schema is None:
        return {"error": ERROR_EXTRACT_JSON_SCHEMA_REQUIRED}, 400
    if not isinstance(json_schema, dict):
        return {"error": ERROR_EXTRACT_JSON_SCHEMA_TYPE}, 400

    headers = arguments.get("headers")
    max_content_length = DEFAULT_FETCH_CONTENT_LIMIT
    if max_content_length is not None:
        max_content_length = min(int(max_content_length), MAX_FETCH_CONTENT_LIMIT)

    fetch_result = await asyncio.to_thread(client.fetch, url, headers)
    if "error" in fetch_result:
        return {
            "error": ERROR_FETCH_PREFIX.format(error=fetch_result["error"]),
            "stage": "fetch",
        }, 200

    content = fetch_result.get("content", "")
    if max_content_length is not None and len(content) > max_content_length:
        content = truncate_content_with_links(content, max_content_length)

    if not str(content).strip():
        return {"error": ERROR_EXTRACT_CONTENT_EMPTY}, 400

    if len(content) > EXTRACT_MAX_LENGTH:
        return {"error": ERROR_EXTRACT_CONTENT_TOO_LONG.format(limit=EXTRACT_MAX_LENGTH)}, 413

    sidecar_body: Dict[str, Any] = {
        "content": content,
        "source_url": url,
        "json_schema": json_schema,
        "content_format": EXTRACT_SIDECAR_CONTENT_FORMAT,
    }
    if arguments.get("prompt") is not None:
        sidecar_body["prompt"] = arguments.get("prompt")

    return await post_sidecar_extract(sidecar_body)
