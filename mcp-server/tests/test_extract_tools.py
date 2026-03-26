"""Tests for extract tool registration and helpers."""

from server import build_tool_definitions, parse_env_bool, tools_to_json_list


def test_build_tool_definitions_without_extract():
    tools = build_tool_definitions(False)
    names = [t.name for t in tools]
    assert "search" in names
    assert "fetch" in names
    assert "crawl" in names
    assert "extract" not in names


def test_build_tool_definitions_with_extract():
    tools = build_tool_definitions(True)
    names = [t.name for t in tools]
    assert "extract" in names


def test_tools_endpoint_shape():
    tools = tools_to_json_list(build_tool_definitions(True))
    extract = next(t for t in tools if t["name"] == "extract")
    assert "inputSchema" in extract
    assert "url" in extract["inputSchema"]["properties"]
    assert "json_schema" in extract["inputSchema"]["properties"]


def test_parse_env_bool():
    assert parse_env_bool("X_TEST_UNSET", True) is True
    assert parse_env_bool("X_TEST_UNSET", False) is False
