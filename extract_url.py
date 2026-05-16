#!/usr/bin/env python3
"""
CLI for MCP extract: one POST to searxng-mcp /extract (fetch + sidecar).

Usage:
  extract_url <url> --keys title,author,summary
  extract_url <url> --keys title,summary --prompt "Main article only; ignore nav"
  extract_url <url> --json '{"title":"Page title","summary":"Short summary"}'

Environment (optional):
  SEARXNG_MCP_HOST   default localhost
  SEARXNG_MCP_PORT   default 7778
  EXTRACT_TIMEOUT    curl --max-time seconds (default 120)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ENV_MCP_HOST = "SEARXNG_MCP_HOST"
ENV_MCP_PORT = "SEARXNG_MCP_PORT"
ENV_EXTRACT_TIMEOUT = "EXTRACT_TIMEOUT"

DEFAULT_MCP_HOST = "localhost"
DEFAULT_MCP_PORT = "7778"
DEFAULT_EXTRACT_TIMEOUT_SECONDS = 120
DEFAULT_HEALTH_TIMEOUT_SECONDS = 5

HEALTH_STATUS_OK = "healthy"
MCP_HEALTH_PATH = "/health"
MCP_EXTRACT_PATH = "/extract"

RESERVED_SCHEMA_KEY_PROMPT = "prompt"


def mcp_base_url() -> str:
    host = os.environ.get(ENV_MCP_HOST, DEFAULT_MCP_HOST)
    port = os.environ.get(ENV_MCP_PORT, DEFAULT_MCP_PORT)
    return f"http://{host}:{port}"


def extract_timeout_seconds() -> int:
    raw = os.environ.get(ENV_EXTRACT_TIMEOUT, str(DEFAULT_EXTRACT_TIMEOUT_SECONDS))
    return int(raw)


def humanize_key(key: str) -> str:
    words = re.sub(r"[_\-]+", " ", key.strip()).split()
    return " ".join(w.capitalize() for w in words)


def keys_to_simple_schema(keys_csv: str) -> Dict[str, str]:
    keys = [k.strip() for k in keys_csv.split(",") if k.strip()]
    if not keys:
        raise ValueError("--keys must list at least one field name")
    return {key: humanize_key(key) for key in keys}


def simple_object_to_json_schema(
    simple: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Map {field: description, prompt?: ...} to JSON Schema subset for /extract."""
    prompt: Optional[str] = None
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for key, value in simple.items():
        if key == RESERVED_SCHEMA_KEY_PROMPT:
            if value is not None and str(value).strip():
                prompt = str(value)
            continue
        if not isinstance(key, str) or not key.strip():
            raise ValueError("schema field names must be non-empty strings")
        description = str(value) if value is not None else humanize_key(key)
        properties[key] = {"type": "string", "description": description}
        required.append(key)

    if not properties:
        raise ValueError(
            "schema must define at least one field "
            f"(use --keys or --json without only '{RESERVED_SCHEMA_KEY_PROMPT}')"
        )

    return (
        {
            "type": "object",
            "properties": properties,
            "required": required,
        },
        prompt,
    )


def curl_json(
    method: str,
    url: str,
    body: Optional[Dict[str, Any]] = None,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    cmd = ["curl", "-sS", "-X", method, url, "-H", "Content-Type: application/json"]
    if timeout_seconds is not None:
        cmd.extend(["--max-time", str(timeout_seconds)])

    tmp_path: Optional[str] = None
    try:
        if body is not None:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".json",
                delete=False,
            ) as tmp:
                json.dump(body, tmp, ensure_ascii=False)
                tmp_path = tmp.name
            cmd.extend(["-d", f"@{tmp_path}"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0:
        raise RuntimeError(
            f"curl failed (exit {result.returncode}): {stderr.strip() or stdout.strip()}"
        )

    try:
        parsed = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"response is not JSON: {stdout[:500]}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("response JSON must be an object")

    return parsed


def ensure_mcp_available() -> None:
    base = mcp_base_url()
    health_url = f"{base}{MCP_HEALTH_PATH}"
    try:
        body = curl_json(
            "GET",
            health_url,
            timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
        )
    except RuntimeError as exc:
        raise RuntimeError(
            f"searxng-mcp is not reachable at {base} ({exc}). "
            "Start services with: docker compose up -d"
        ) from exc
    if body.get("status") != HEALTH_STATUS_OK:
        raise RuntimeError(
            f"searxng-mcp at {base} is not healthy "
            f"(GET {MCP_HEALTH_PATH} returned {body!r})"
        )


def mcp_extract(
    url: str,
    json_schema: Dict[str, Any],
    prompt: Optional[str],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"url": url, "json_schema": json_schema}
    if prompt:
        payload["prompt"] = prompt

    body = curl_json(
        "POST",
        f"{mcp_base_url()}{MCP_EXTRACT_PATH}",
        payload,
        timeout_seconds=extract_timeout_seconds(),
    )
    if "error" in body:
        stage = body.get("stage")
        if stage:
            raise RuntimeError(f"extract failed ({stage}): {body['error']}")
        raise RuntimeError(f"extract failed: {body['error']}")
    return body


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch a URL and extract structured fields via searxng-mcp POST /extract.",
    )
    parser.add_argument("url", help="Page URL to fetch and extract from")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--keys",
        metavar="NAMES",
        help="Comma-separated field names (string properties, auto descriptions)",
    )
    group.add_argument(
        "--json",
        dest="json_schema",
        metavar="OBJECT",
        help=(
            "Simple JSON object: each key is a field, each value is its description"
        ),
    )
    parser.add_argument(
        "--prompt",
        metavar="TEXT",
        help=(
            "Extraction instructions for the LLM (paired with the schema; "
            "overrides a prompt key inside --json if both are given)"
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        ensure_mcp_available()
        if args.keys:
            simple = keys_to_simple_schema(args.keys)
        else:
            simple = json.loads(args.json_schema)
            if not isinstance(simple, dict):
                raise ValueError("--json must be a JSON object")

        json_schema, schema_prompt = simple_object_to_json_schema(simple)
        prompt = (args.prompt or "").strip() or schema_prompt
        result = mcp_extract(args.url, json_schema, prompt)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    data = result.get("data")
    if data is None:
        raise RuntimeError("extract response missing data field")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
