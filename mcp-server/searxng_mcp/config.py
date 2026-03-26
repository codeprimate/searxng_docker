"""Configuration constants and environment-derived settings for the SearXNG MCP server."""

import logging
import os

logger = logging.getLogger(__name__)

# Network & Timeout Settings
DEFAULT_TIMEOUT = 5
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Content Limits (set to None for no truncation by default)
DEFAULT_FETCH_CONTENT_LIMIT = None  # No truncation by default
DEFAULT_SEARCH_SNIPPET_LIMIT = None  # No truncation by default
DEFAULT_SEARCH_RESULTS_LIMIT = 20  # Configurable search results limit

# Crawl Limits
DEFAULT_SUBPAGE_LIMIT = 5
MAX_SUBPAGE_LIMIT = 10

# Safety Limits (hard limits to prevent abuse)
MAX_FETCH_CONTENT_LIMIT = 1024 * 1024  # 1MB hard limit
MAX_SEARCH_SNIPPET_LIMIT = 10000  # 10k chars hard limit
MAX_SEARCH_RESULTS_LIMIT = 100  # 100 results hard limit

# Error messages
ERROR_QUERY_REQUIRED = "Error: Query is required"
ERROR_URL_REQUIRED = "Error: URL is required"
ERROR_UNKNOWN_TOOL = "Unknown tool: {name}"
ERROR_SEARCH_PREFIX = "Search error: {error}"
ERROR_FETCH_PREFIX = "Fetch error: {error}"
ERROR_CRAWL_PREFIX = "Crawl error: {error}"

# Response formatting
NO_RESULTS_FOUND = "No results found"
CONTENT_TRUNCATED = "...\n[Content truncated]"
LINKS_SECTION_MARKER = "\n\nLinks found on this page:"

# Extract tool (MCP fetch + extractor sidecar)
ENV_EXTRACT_ENABLED = "EXTRACT_ENABLED"
ENV_EXTRACT_TIMEOUT = "EXTRACT_TIMEOUT"
ENV_EXTRACT_MAX_LENGTH = "EXTRACT_MAX_LENGTH"
ENV_EXTRACT_MAX_JSON_BODY_BYTES = "EXTRACT_MAX_JSON_BODY_BYTES"
ENV_EXTRACTOR_SIDECAR_URL = "EXTRACTOR_SIDECAR_URL"

DEFAULT_EXTRACT_ENABLED = False
DEFAULT_EXTRACT_TIMEOUT_SECONDS = 120
KIBIBYTE = 1024
DEFAULT_EXTRACT_MAX_LENGTH = 512 * KIBIBYTE  # 512 KiB `content` cap
DEFAULT_EXTRACT_MAX_JSON_BODY_BYTES = 512 * KIBIBYTE  # 512 KiB raw POST body cap

# Aligns with SearXNGClient.fetch(): content is always HTML-stripped plain text.
EXTRACT_SIDECAR_CONTENT_FORMAT = "txt"

ERROR_EXTRACT_DISABLED = "Error: extract is disabled (set EXTRACT_ENABLED=true)"
ERROR_EXTRACT_JSON_SCHEMA_REQUIRED = "Error: json_schema is required"
ERROR_EXTRACT_JSON_SCHEMA_TYPE = "Error: json_schema must be an object"
ERROR_EXTRACT_CONTENT_EMPTY = (
    "Error: fetched content is empty or whitespace-only after cleaning"
)
ERROR_EXTRACT_CONTENT_TOO_LONG = (
    "Error: content exceeds EXTRACT_MAX_LENGTH ({limit} Unicode code units)"
)
ERROR_EXTRACT_SIDECAR_URL = "Error: EXTRACTOR_SIDECAR_URL is not set"
ERROR_EXTRACT_HTTP_DISABLED = "extract disabled"
CODE_EXTRACT_DISABLED = "EXTRACT_DISABLED"


def parse_env_bool(env_name: str, default: bool) -> bool:
    raw = os.environ.get(env_name)
    if raw is None or str(raw).strip() == "":
        return default
    v = str(raw).strip().lower()
    if v in ("1", "true", "yes"):
        return True
    if v in ("0", "false", "no"):
        return False
    logger.warning(
        "Invalid boolean for %s: %r; using default %s", env_name, raw, default
    )
    return default


def parse_env_int(env_name: str, default: int) -> int:
    raw = os.environ.get(env_name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        logger.warning(
            "Invalid integer for %s: %r; using default %s", env_name, raw, default
        )
        return default


EXTRACT_ENABLED = parse_env_bool(ENV_EXTRACT_ENABLED, DEFAULT_EXTRACT_ENABLED)
EXTRACT_TIMEOUT_SECONDS = parse_env_int(ENV_EXTRACT_TIMEOUT, DEFAULT_EXTRACT_TIMEOUT_SECONDS)
EXTRACT_MAX_LENGTH = parse_env_int(ENV_EXTRACT_MAX_LENGTH, DEFAULT_EXTRACT_MAX_LENGTH)
EXTRACT_MAX_JSON_BODY_BYTES = parse_env_int(
    ENV_EXTRACT_MAX_JSON_BODY_BYTES,
    DEFAULT_EXTRACT_MAX_JSON_BODY_BYTES,
)
EXTRACTOR_SIDECAR_URL = os.environ.get(ENV_EXTRACTOR_SIDECAR_URL)
if EXTRACTOR_SIDECAR_URL:
    EXTRACTOR_SIDECAR_URL = EXTRACTOR_SIDECAR_URL.strip() or None
