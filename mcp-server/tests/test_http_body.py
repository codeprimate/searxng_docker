"""Tests for HTTP response body decompression."""

import gzip

from searxng_mcp.http_body import (
    decode_http_response_body,
    decompress_http_body,
    looks_like_gzip,
)


def test_looks_like_gzip():
    raw = gzip.compress(b"hello")
    assert looks_like_gzip(raw) is True
    assert looks_like_gzip(b"plain text") is False


def test_decompress_gzip_by_content_encoding():
    raw = gzip.compress(b"<html>ok</html>")
    assert decompress_http_body(raw, "gzip") == b"<html>ok</html>"


def test_decompress_gzip_by_magic_without_header():
    raw = gzip.compress(b"payload")
    assert decompress_http_body(raw, None) == b"payload"


def test_plain_body_unchanged():
    raw = b"<!DOCTYPE html><title>Example</title>"
    assert decompress_http_body(raw, None) == raw


def test_decode_http_response_body_gzip_header():
    raw = gzip.compress("café".encode("utf-8"))
    headers = {"Content-Encoding": "gzip", "Content-Type": "text/html; charset=utf-8"}
    assert decode_http_response_body(raw, headers) == "café"


def test_decode_http_response_body_no_compression():
    raw = b"Hello"
    headers = {"Content-Type": "text/plain"}
    assert decode_http_response_body(raw, headers) == "Hello"
