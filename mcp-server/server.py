#!/usr/bin/env python3
"""
SearXNG MCP Server - Self-contained MCP server for SearXNG search engine.
"""

import asyncio
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Web server imports
import aiohttp
from aiohttp import web, web_request

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Network & Timeout Settings
DEFAULT_TIMEOUT = 5
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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

# Aligns with SearXNGClient.fetch(): content is always HTML-stripped plain text, not Markdown or raw HTML.
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

logger = logging.getLogger(__name__)


def parse_env_bool(env_name: str, default: bool) -> bool:
    raw = os.environ.get(env_name)
    if raw is None or str(raw).strip() == "":
        return default
    v = str(raw).strip().lower()
    if v in ("1", "true", "yes"):
        return True
    if v in ("0", "false", "no"):
        return False
    logger.warning("Invalid boolean for %s: %r; using default %s", env_name, raw, default)
    return default


def parse_env_int(env_name: str, default: int) -> int:
    raw = os.environ.get(env_name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        logger.warning("Invalid integer for %s: %r; using default %s", env_name, raw, default)
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


# Embedded SearXNG Client
class SearXNGClient:
    def __init__(self, base_url: str = None, timeout: int = DEFAULT_TIMEOUT):
        if base_url is None:
            protocol = os.environ.get('SEARXNG_PROTOCOL', 'http')
            host = os.environ.get('SEARXNG_HOST', 'searxng')
            port = os.environ.get('SEARXNG_PORT', '7777')
            base_url = f"{protocol}://{host}:{port}"
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.search_url = f"{self.base_url}/search"
    
    def search(self, query: str, categories: Optional[List[str]] = None,
               engines: Optional[List[str]] = None, language: str = "en",
               time_range: Optional[str] = None, pageno: int = 1) -> Dict[str, Any]:
        params = {
            'q': query,
            'format': 'json',
            'language': language,
            'safesearch': 0,  # Always off
            'pageno': pageno
        }
        
        if categories:
            params['categories'] = ','.join(categories)
        if engines:
            params['engines'] = ','.join(engines)
        if time_range:
            params['time_range'] = time_range
        
        url = f"{self.search_url}?{urllib.parse.urlencode(params)}"
        
        try:
            request = urllib.request.Request(url)
            request.add_header('User-Agent', DEFAULT_USER_AGENT)
            
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content = response.read().decode('utf-8')
                return json.loads(content)
        except Exception as e:
            return {'error': str(e)}
    
    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Fetch content from a URL and return clean text (HTML stripped)"""
        try:
            request = urllib.request.Request(url)
            request.add_header('User-Agent', DEFAULT_USER_AGENT)
            
            # Add custom headers if provided
            if headers:
                for key, value in headers.items():
                    request.add_header(key, value)
            
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw_content = response.read().decode('utf-8')
                
                # Parse HTML and extract clean text
                soup = BeautifulSoup(raw_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get clean text
                clean_text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in clean_text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Extract links after getting clean text
                links = []
                seen_urls = set()  # Track seen URLs to avoid duplicates
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    anchor_text = link.get_text(strip=True)
                    if href and anchor_text:
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(url, href)
                        # Only add if we haven't seen this URL before
                        if absolute_url not in seen_urls:
                            seen_urls.add(absolute_url)
                            links.append(f"{anchor_text}: {absolute_url}")
                
                # Append links to the clean text
                if links:
                    clean_text += "\n\nLinks found on this page:\n" + "\n".join(links)
                
                return {
                    'url': url,
                    'status_code': response.status,
                    'headers': dict(response.headers),
                    'content': clean_text,
                    'content_length': len(clean_text),
                    'original_content_length': len(raw_content)
                }
        except Exception as e:
            return {'error': str(e), 'url': url}
    
    def crawl(self, url: str, filters: Optional[List[str]] = None, 
              headers: Optional[Dict[str, str]] = None, subpage_limit: int = DEFAULT_SUBPAGE_LIMIT,
              max_content_length: Optional[int] = None) -> Dict[str, Any]:
        """Crawl a page and return its content plus up to subpage_limit subpages that match filter criteria"""
        try:
            # First, fetch the main page content
            main_result = self.fetch(url, headers)
            if 'error' in main_result:
                return main_result
            
            # Parse the main page to extract links
            request = urllib.request.Request(url)
            request.add_header('User-Agent', DEFAULT_USER_AGENT)
            
            if headers:
                for key, value in headers.items():
                    request.add_header(key, value)
            
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw_content = response.read().decode('utf-8')
                soup = BeautifulSoup(raw_content, 'html.parser')
            
            # Extract all links with their anchor text
            links = []
            seen_urls = set()  # Track seen URLs to avoid duplicates
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                anchor_text = link.get_text(strip=True)
                
                if href and anchor_text:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(url, href)
                    
                    # Skip if we've already seen this URL
                    if absolute_url in seen_urls:
                        continue
                    seen_urls.add(absolute_url)
                    
                    # Check if link matches any filter criteria
                    if filters:
                        # Check if any filter string is contained in the anchor text (case-insensitive)
                        if not any(filter_str.lower() in anchor_text.lower() for filter_str in filters):
                            continue
                    
                    links.append({
                        'url': absolute_url,
                        'anchor_text': anchor_text
                    })
            
            # Limit to subpage_limit subpages
            selected_links = links[:subpage_limit]
            
            # Fetch content for each selected subpage
            subpages = []
            for link_info in selected_links:
                subpage_result = self.fetch(link_info['url'], headers)
                if 'error' not in subpage_result:
                    content = subpage_result['content']
                    content_length = subpage_result['content_length']
                    
                    # Apply content length limit if specified
                    if max_content_length is not None and len(content) > max_content_length:
                        content = truncate_content_with_links(content, max_content_length)
                        content_length = len(content)
                    
                    subpages.append({
                        'url': link_info['url'],
                        'anchor_text': link_info['anchor_text'],
                        'content': content,
                        'content_length': content_length
                    })
            
            return {
                'main_page': {
                    'url': url,
                    'content': main_result['content'],
                    'content_length': main_result['content_length']
                },
                'subpages': subpages,
                'total_subpages_found': len(links),
                'subpages_returned': len(subpages),
                'filters_applied': filters
            }
            
        except Exception as e:
            return {'error': str(e), 'url': url}

# Helper functions for content processing
def truncate_content_with_links(content: str, max_length: int) -> str:
    """Truncate content while preserving links section if present."""
    if max_length is None or len(content) <= max_length:
        return content
    
    links_section_start = content.find(LINKS_SECTION_MARKER)
    if links_section_start != -1:
        # Truncate main content but keep links section
        main_content = content[:links_section_start]
        links_section = content[links_section_start:]
        if len(main_content) > max_length:
            main_content = main_content[:max_length] + CONTENT_TRUNCATED
        return main_content + links_section
    else:
        return content[:max_length] + CONTENT_TRUNCATED

def create_error_response(message: str) -> List[TextContent]:
    """Create a standardized error response."""
    return [TextContent(type="text", text=message)]

def parse_comma_separated(value: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated string into list, return None if empty."""
    return value.split(',') if value else None


def build_tool_definitions(extract_enabled: bool) -> List[Tool]:
    """Single source of truth for MCP list_tools and HTTP /tools."""
    tools: List[Tool] = [
        Tool(
            name="search",
            description="Search using SearXNG metasearch engine",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "categories": {"type": "string", "description": "Comma-separated categories (general,it,videos,images)"},
                    "engines": {"type": "string", "description": "Comma-separated engines (bing,duckduckgo,google,startpage,wikipedia,github,reddit,youtube,stackexchange,etc.)"},
                    "language": {"type": "string", "description": "Language code (default: en)"},
                    "time_range": {"type": "string", "description": "Time range for search results (day, month, year)"},
                    "pageno": {"type": "integer", "description": "Page number for pagination (default: 1)"},
                    "max_results": {"type": "integer", "description": f"Maximum number of results to return (default: {DEFAULT_SEARCH_RESULTS_LIMIT}, max: {MAX_SEARCH_RESULTS_LIMIT})"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="fetch",
            description="Fetch content from a URL and return clean text (HTML stripped)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch content from"},
                    "headers": {"type": "object", "description": "Optional custom headers as key-value pairs"},
                    "max_content_length": {"type": "integer", "description": f"Maximum content length in characters (default: no limit, max: {MAX_FETCH_CONTENT_LIMIT})"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="crawl",
            description="Crawl a page and return its content plus up to subpage_limit subpages that match filter criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to crawl"},
                    "filters": {"type": "array", "items": {"type": "string"}, "description": "Array of strings to filter anchor text (at least one must match)"},
                    "headers": {"type": "object", "description": "Optional custom headers as key-value pairs"},
                    "subpage_limit": {"type": "integer", "description": f"Maximum number of subpages to crawl (default: {DEFAULT_SUBPAGE_LIMIT}, max: {MAX_SUBPAGE_LIMIT})"},
                    "max_content_length": {"type": "integer", "description": f"Maximum content length per page in characters (default: no limit, max: {MAX_FETCH_CONTENT_LIMIT})"}
                },
                "required": ["url"]
            }
        ),
    ]
    if extract_enabled:
        tools.append(
            Tool(
                name="extract",
                description=(
                    "Fetch a web page URL (same HTML-stripped text as fetch), then return one JSON "
                    "object. You define the extraction task: required json_schema declares the output "
                    "shape; optional prompt adds natural-language rules. Both are arbitrary—pick any "
                    "fields, types, and instructions the task needs. Optional: headers for the fetch."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "HTTP(S) URL of the page to fetch and extract from (required)",
                        },
                        "json_schema": {
                            "type": "object",
                            "description": (
                                "JSON Schema (supported subset) for the single JSON object to return. "
                                "You choose property names, nesting, and types; the result will match "
                                "this schema. Combine with prompt: schema fixes structure, prompt adds "
                                "natural-language extraction rules when needed."
                            ),
                        },
                        "prompt": {
                            "type": "string",
                            "description": (
                                "Optional. Natural-language partner to json_schema: say what to extract "
                                "from the page, how to interpret edge cases, priorities, or formatting—"
                                "anything not captured by the schema alone. Omit when the schema fully "
                                "specifies the task. There is no required wording; you (the caller) "
                                "decide the task together with json_schema."
                            ),
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP request headers for fetching the URL",
                        },
                    },
                    "required": ["url", "json_schema"],
                },
            )
        )
    return tools


def tools_to_json_list(tools_list: List[Tool]) -> List[Dict[str, Any]]:
    return [
        {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
        for t in tools_list
    ]


# MCP Server
app = Server("searxng-mcp")
client = SearXNGClient()

@app.list_tools()
async def list_tools() -> List[Tool]:
    return build_tool_definitions(EXTRACT_ENABLED)

# Tool handler methods
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
    
    # Validate time_range parameter
    if time_range and time_range not in ['day', 'month', 'year']:
        return create_error_response("Error: time_range must be one of: day, month, year")
    
    # Enforce safety limits
    max_results = min(max_results, MAX_SEARCH_RESULTS_LIMIT)
    pageno = max(1, pageno)  # Ensure pageno is at least 1
    
    # Perform search
    results = client.search(query, categories, engines, language, time_range, pageno)
    
    if 'error' in results:
        return create_error_response(ERROR_SEARCH_PREFIX.format(error=results['error']))
    
    # Format results
    if 'results' not in results or not results['results']:
        return [TextContent(type="text", text=NO_RESULTS_FOUND)]
    
    formatted_results = []
    for i, result in enumerate(results['results'][:max_results], 1):
        title = result.get('title', 'N/A')
        url = result.get('url', 'N/A')
        content = result.get('content', '')
        engine = result.get('engine', 'N/A')
        
        # Only truncate content if explicitly requested or exceeds safety limit
        if content and DEFAULT_SEARCH_SNIPPET_LIMIT is not None and len(content) > DEFAULT_SEARCH_SNIPPET_LIMIT:
            content = content[:DEFAULT_SEARCH_SNIPPET_LIMIT] + "..."
        elif content and len(content) > MAX_SEARCH_SNIPPET_LIMIT:
            content = content[:MAX_SEARCH_SNIPPET_LIMIT] + "..."
        
        formatted_results.append(f"{i}. {title}\n   URL: {url}\n   Engine: {engine}\n   Content: {content}\n")
    
    response = f"Search results for '{query}' (showing {len(formatted_results)} of {len(results['results'])} results):\n\n" + "\n".join(formatted_results)
    return [TextContent(type="text", text=response)]

async def handle_fetch_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle fetch tool requests."""
    url = arguments.get("url")
    if not url:
        return create_error_response(ERROR_URL_REQUIRED)
    
    headers = arguments.get("headers")
    max_content_length = arguments.get("max_content_length", DEFAULT_FETCH_CONTENT_LIMIT)
    
    # Enforce safety limits
    if max_content_length is not None:
        max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)
    
    # Perform fetch
    result = client.fetch(url, headers)
    
    if 'error' in result:
        return create_error_response(ERROR_FETCH_PREFIX.format(error=result['error']))
    
    # Format response
    response = f"Fetched content from: {result['url']}\n"
    response += f"Status Code: {result['status_code']}\n"
    if 'original_content_length' in result:
        response += f"Original Content Length: {result['original_content_length']} characters\n"
    response += f"Clean Text Length: {result['content_length']} characters\n\n"
    
    # Apply content length limit if specified
    content = result['content']
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
    
    # Enforce safety limits
    subpage_limit = min(subpage_limit, MAX_SUBPAGE_LIMIT)
    if max_content_length is not None:
        max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)
    
    # Perform crawl
    result = client.crawl(url, filters, headers, subpage_limit, max_content_length)
    
    if 'error' in result:
        return create_error_response(ERROR_CRAWL_PREFIX.format(error=result['error']))
    
    # Format response
    response = f"Crawled: {result['main_page']['url']}\n"
    response += f"Main page content length: {result['main_page']['content_length']} characters\n"
    response += f"Total subpages found: {result['total_subpages_found']}\n"
    response += f"Subpages returned: {result['subpages_returned']}\n"
    
    if result['filters_applied']:
        response += f"Filters applied: {', '.join(result['filters_applied'])}\n"
    
    response += "\n" + "="*50 + "\n"
    response += "MAIN PAGE CONTENT:\n"
    response += "="*50 + "\n"
    
    # Apply content length limit to main page if specified
    main_content = result['main_page']['content']
    if max_content_length is not None and len(main_content) > max_content_length:
        main_content = truncate_content_with_links(main_content, max_content_length)
    
    response += f"{main_content}\n\n"
    
    # Add subpages
    if result['subpages']:
        response += "="*50 + "\n"
        response += "SUBPAGES:\n"
        response += "="*50 + "\n"
        
        for i, subpage in enumerate(result['subpages'], 1):
            response += f"\n{i}. {subpage['anchor_text']}\n"
            response += f"   URL: {subpage['url']}\n"
            response += f"   Content Length: {subpage['content_length']} characters\n"
            
            # Content is already truncated in the crawl method if needed
            response += f"   Content: {subpage['content']}\n"
            response += "-" * 30 + "\n"
    
    return [TextContent(type="text", text=response)]


async def post_sidecar_extract(payload: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
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


async def run_extract_pipeline(arguments: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
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


async def handle_extract_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    if not EXTRACT_ENABLED:
        return create_error_response(ERROR_EXTRACT_DISABLED)
    body, status = await run_extract_pipeline(arguments)
    if status >= 400:
        return create_error_response(str(body.get("error", "extract failed")))
    if body.get("error"):
        return create_error_response(str(body["error"]))
    return [TextContent(type="text", text=json.dumps(body, ensure_ascii=False))]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch tool calls to appropriate handlers."""
    if name == "extract" and not EXTRACT_ENABLED:
        return create_error_response(ERROR_EXTRACT_DISABLED)

    tool_handlers = {
        "search": handle_search_tool,
        "fetch": handle_fetch_tool,
        "crawl": handle_crawl_tool,
    }
    if EXTRACT_ENABLED:
        tool_handlers["extract"] = handle_extract_tool

    handler = tool_handlers.get(name)
    if handler:
        return await handler(arguments)

    return create_error_response(ERROR_UNKNOWN_TOOL.format(name=name))

# Web server routes
async def search_endpoint(request: web_request.Request) -> web.Response:
    try:
        data = await request.json()
        query = data.get('query')
        if not query:
            return web.json_response({'error': 'Query is required'}, status=400)
        
        categories = data.get('categories')
        engines = data.get('engines')
        language = data.get('language', 'en')
        time_range = data.get('time_range')
        pageno = data.get('pageno', 1)
        max_results = data.get('max_results', DEFAULT_SEARCH_RESULTS_LIMIT)
        
        # Validate time_range parameter
        if time_range and time_range not in ['day', 'month', 'year']:
            return web.json_response({'error': 'time_range must be one of: day, month, year'}, status=400)
        
        # Parse comma-separated strings
        categories_list = categories.split(',') if categories else None
        engines_list = engines.split(',') if engines else None
        
        # Enforce safety limits
        max_results = min(max_results, MAX_SEARCH_RESULTS_LIMIT)
        pageno = max(1, pageno)  # Ensure pageno is at least 1
        
        # Perform search
        results = client.search(query, categories_list, engines_list, language, time_range, pageno)
        
        # Apply result limit
        if 'results' in results and results['results']:
            results['results'] = results['results'][:max_results]
        
        return web.json_response(results)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def health_endpoint(request: web_request.Request) -> web.Response:
    return web.json_response({'status': 'healthy'})

async def fetch_endpoint(request: web_request.Request) -> web.Response:
    try:
        data = await request.json()
        url = data.get('url')
        if not url:
            return web.json_response({'error': 'URL is required'}, status=400)
        
        headers = data.get('headers')
        max_content_length = data.get('max_content_length', DEFAULT_FETCH_CONTENT_LIMIT)
        
        # Enforce safety limits
        if max_content_length is not None:
            max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)
        
        # Perform fetch
        result = client.fetch(url, headers)
        
        # Apply content length limit if specified
        if 'content' in result and max_content_length is not None and len(result['content']) > max_content_length:
            result['content'] = truncate_content_with_links(result['content'], max_content_length)
            result['content_length'] = len(result['content'])
        
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def crawl_endpoint(request: web_request.Request) -> web.Response:
    try:
        data = await request.json()
        url = data.get('url')
        if not url:
            return web.json_response({'error': 'URL is required'}, status=400)
        
        filters = data.get('filters')
        headers = data.get('headers')
        subpage_limit = data.get('subpage_limit', DEFAULT_SUBPAGE_LIMIT)
        max_content_length = data.get('max_content_length', DEFAULT_FETCH_CONTENT_LIMIT)
        
        # Enforce safety limits
        subpage_limit = min(subpage_limit, MAX_SUBPAGE_LIMIT)
        if max_content_length is not None:
            max_content_length = min(max_content_length, MAX_FETCH_CONTENT_LIMIT)
        
        # Perform crawl
        result = client.crawl(url, filters, headers, subpage_limit, max_content_length)
        
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

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
    app_web.router.add_post('/search', search_endpoint)
    app_web.router.add_post('/fetch', fetch_endpoint)
    app_web.router.add_post('/crawl', crawl_endpoint)
    app_web.router.add_post('/extract', extract_endpoint)
    app_web.router.add_get('/health', health_endpoint)
    app_web.router.add_get('/tools', tools_endpoint)
    return app_web

async def main():
    # Check if running as web server or MCP server
    if len(sys.argv) > 1 and sys.argv[1] == '--web':
        # Run as web server
        app_web = await create_web_app()
        port = int(os.environ.get('PORT', 7778))
        runner = web.AppRunner(app_web)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"Web server running on port {port}")
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            pass
    else:
        # Run as MCP server
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
