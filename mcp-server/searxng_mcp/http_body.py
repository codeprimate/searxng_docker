"""Decode HTTP response bodies (gzip/deflate and charset)."""

import gzip
import re
import zlib
from typing import Any, Mapping, Optional

GZIP_MAGIC = b"\x1f\x8b"
DEFAULT_RESPONSE_CHARSET = "utf-8"
CONTENT_ENCODING_GZIP = frozenset({"gzip", "x-gzip"})
CONTENT_ENCODING_DEFLATE = frozenset({"deflate"})
_CHARSET_RE = re.compile(r"charset=([^\s;]+)", re.IGNORECASE)


def _header_value(headers: Mapping[str, Any], name: str) -> Optional[str]:
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    return getter(name) or getter(name.lower())


def primary_content_encoding(headers: Mapping[str, Any]) -> Optional[str]:
    """First token of Content-Encoding (e.g. gzip from 'gzip, br')."""
    value = _header_value(headers, "Content-Encoding")
    if not value:
        return None
    return value.split(",")[0].strip().lower()


def charset_from_content_type(headers: Mapping[str, Any]) -> str:
    content_type = _header_value(headers, "Content-Type") or ""
    match = _CHARSET_RE.search(content_type)
    if match:
        return match.group(1).strip("\"'")
    return DEFAULT_RESPONSE_CHARSET


def looks_like_gzip(raw: bytes) -> bool:
    return len(raw) >= 2 and raw[:2] == GZIP_MAGIC


def decompress_http_body(raw: bytes, content_encoding: Optional[str] = None) -> bytes:
    """Decompress body when Content-Encoding or gzip magic indicates compression."""
    encoding = (content_encoding or "").lower()
    if encoding in CONTENT_ENCODING_GZIP or looks_like_gzip(raw):
        return gzip.decompress(raw)
    if encoding in CONTENT_ENCODING_DEFLATE:
        return zlib.decompress(raw)
    return raw


def decode_http_response_body(raw: bytes, headers: Mapping[str, Any]) -> str:
    """Return text from raw HTTP response bytes and response headers."""
    decompressed = decompress_http_body(raw, primary_content_encoding(headers))
    charset = charset_from_content_type(headers)
    return decompressed.decode(charset)
