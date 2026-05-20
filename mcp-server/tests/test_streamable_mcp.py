"""Tests for streamable HTTP MCP at MCP_STREAMABLE_PATH."""

import os

import pytest
from starlette.testclient import TestClient

# Ensure streamable MCP is enabled before importing app factory
os.environ.setdefault("MCP_STREAMABLE_ENABLED", "true")
os.environ.setdefault("MCP_JSON_RESPONSE", "true")
os.environ.setdefault("MCP_STATELESS_HTTP", "true")

from searxng_mcp.config import MCP_STREAMABLE_PATH  # noqa: E402
from searxng_mcp.http.routes import create_web_app  # noqa: E402

MCP_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

INITIALIZE_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "1.0"},
    },
}


@pytest.fixture
def web_client():
    with TestClient(create_web_app()) as client:
        yield client


def test_health_endpoint(web_client):
    response = web_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_streamable_initialize(web_client):
    response = web_client.post(
        MCP_STREAMABLE_PATH,
        json=INITIALIZE_BODY,
        headers=MCP_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("jsonrpc") == "2.0"
    assert body.get("id") == 1
    assert "result" in body
    assert body["result"].get("serverInfo", {}).get("name") == "searxng-mcp"


def test_streamable_list_tools(web_client):
    init = web_client.post(
        MCP_STREAMABLE_PATH,
        json=INITIALIZE_BODY,
        headers=MCP_HEADERS,
    )
    assert init.status_code == 200

    list_body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    response = web_client.post(
        MCP_STREAMABLE_PATH,
        json=list_body,
        headers=MCP_HEADERS,
    )
    assert response.status_code == 200
    result = response.json().get("result", {})
    names = {t["name"] for t in result.get("tools", [])}
    assert "search" in names
    assert "fetch" in names
    assert "crawl" in names
