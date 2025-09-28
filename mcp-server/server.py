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
from aiohttp import web, web_request

# Configuration
DEFAULT_TIMEOUT = 30
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MAX_FETCH_LENGTH = 16384  # 16k characters default for full page content
MAX_SEARCH_CONTENT_LENGTH = 200  # 200 characters for search result snippets

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
               engines: Optional[List[str]] = None, language: str = "en") -> Dict[str, Any]:
        params = {
            'q': query,
            'format': 'json',
            'lang': language
        }
        
        if categories:
            params['categories'] = ','.join(categories)
        if engines:
            params['engines'] = ','.join(engines)
        
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
              headers: Optional[Dict[str, str]] = None, subpage_limit: int = 5) -> Dict[str, Any]:
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
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                anchor_text = link.get_text(strip=True)
                
                if href and anchor_text:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(url, href)
                    
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
                    subpages.append({
                        'url': link_info['url'],
                        'anchor_text': link_info['anchor_text'],
                        'content': subpage_result['content'],
                        'content_length': subpage_result['content_length']
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

# MCP Server
app = Server("searxng-mcp")
client = SearXNGClient()

@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="search",
            description="Search using SearXNG metasearch engine",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "categories": {"type": "string", "description": "Comma-separated categories (optional)"},
                    "engines": {"type": "string", "description": "Comma-separated engines (optional)"},
                    "language": {"type": "string", "description": "Language code (default: en)"}
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
                    "headers": {"type": "object", "description": "Optional custom headers as key-value pairs"}
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
                    "subpage_limit": {"type": "integer", "description": "Maximum number of subpages to crawl (default: 5)"}
                },
                "required": ["url"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    if name == "search":
        query = arguments.get("query")
        if not query:
            return [TextContent(type="text", text="Error: Query is required")]
        
        categories = arguments.get("categories")
        engines = arguments.get("engines")
        language = arguments.get("language", "en")
        
        # Parse comma-separated strings
        categories_list = categories.split(',') if categories else None
        engines_list = engines.split(',') if engines else None
        
        # Perform search
        results = client.search(query, categories_list, engines_list, language)
        
        if 'error' in results:
            return [TextContent(type="text", text=f"Search error: {results['error']}")]
        
        # Format results
        if 'results' not in results or not results['results']:
            return [TextContent(type="text", text="No results found")]
        
        formatted_results = []
        for i, result in enumerate(results['results'][:10], 1):
            title = result.get('title', 'N/A')
            url = result.get('url', 'N/A')
            content = result.get('content', '')
            engine = result.get('engine', 'N/A')
            
            if content and len(content) > MAX_SEARCH_CONTENT_LENGTH:
                content = content[:MAX_SEARCH_CONTENT_LENGTH] + "..."
            
            formatted_results.append(f"{i}. {title}\n   URL: {url}\n   Engine: {engine}\n   Content: {content}\n")
        
        response = f"Search results for '{query}':\n\n" + "\n".join(formatted_results)
        return [TextContent(type="text", text=response)]
    
    elif name == "fetch":
        url = arguments.get("url")
        if not url:
            return [TextContent(type="text", text="Error: URL is required")]
        
        headers = arguments.get("headers")
        
        # Perform fetch
        result = client.fetch(url, headers)
        
        if 'error' in result:
            return [TextContent(type="text", text=f"Fetch error: {result['error']}")]
        
        # Format response
        response = f"Fetched content from: {result['url']}\n"
        response += f"Status Code: {result['status_code']}\n"
        if 'original_content_length' in result:
            response += f"Original Content Length: {result['original_content_length']} characters\n"
        response += f"Clean Text Length: {result['content_length']} characters\n\n"
        
        # Truncate content if too long
        content = result['content']
        if len(content) > MAX_FETCH_LENGTH:
            content = content[:MAX_FETCH_LENGTH] + "...\n[Content truncated]"
        
        response += f"Clean Text Content:\n{content}"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "crawl":
        url = arguments.get("url")
        if not url:
            return [TextContent(type="text", text="Error: URL is required")]
        
        filters = arguments.get("filters")
        headers = arguments.get("headers")
        subpage_limit = arguments.get("subpage_limit", 5)
        
        # Perform crawl
        result = client.crawl(url, filters, headers, subpage_limit)
        
        if 'error' in result:
            return [TextContent(type="text", text=f"Crawl error: {result['error']}")]
        
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
        
        # Truncate main page content if too long
        main_content = result['main_page']['content']
        if len(main_content) > MAX_FETCH_LENGTH:
            main_content = main_content[:MAX_FETCH_LENGTH] + "...\n[Content truncated]"
        
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
                
                # Truncate subpage content if too long
                subpage_content = subpage['content']
                if len(subpage_content) > MAX_SEARCH_CONTENT_LENGTH:
                    subpage_content = subpage_content[:MAX_SEARCH_CONTENT_LENGTH] + "...\n[Content truncated]"
                
                response += f"   Content: {subpage_content}\n"
                response += "-" * 30 + "\n"
        
        return [TextContent(type="text", text=response)]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

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
        
        # Parse comma-separated strings
        categories_list = categories.split(',') if categories else None
        engines_list = engines.split(',') if engines else None
        
        # Perform search
        results = client.search(query, categories_list, engines_list, language)
        
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
        
        # Perform fetch
        result = client.fetch(url, headers)
        
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
        subpage_limit = data.get('subpage_limit', 5)
        
        # Enforce maximum limit of 10 subpages
        subpage_limit = min(subpage_limit, 10)
        
        # Perform crawl
        result = client.crawl(url, filters, headers, subpage_limit)
        
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def tools_endpoint(request: web_request.Request) -> web.Response:
    tools = [
        {
            "name": "search",
            "description": "Search using SearXNG metasearch engine",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "categories": {"type": "string", "description": "Comma-separated categories (optional)"},
                    "engines": {"type": "string", "description": "Comma-separated engines (optional)"},
                    "language": {"type": "string", "description": "Language code (default: en)"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch",
            "description": "Fetch content from a URL and return clean text (HTML stripped)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch content from"},
                    "headers": {"type": "object", "description": "Optional custom headers as key-value pairs"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "crawl",
            "description": "Crawl a page and return its content plus up to subpage_limit subpages that match filter criteria",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to crawl"},
                    "filters": {"type": "array", "items": {"type": "string"}, "description": "Array of strings to filter anchor text (at least one must match)"},
                    "headers": {"type": "object", "description": "Optional custom headers as key-value pairs"},
                    "subpage_limit": {"type": "integer", "description": "Maximum number of subpages to crawl (default: 5)"}
                },
                "required": ["url"]
            }
        }
    ]
    return web.json_response({'tools': tools})

async def create_web_app() -> web.Application:
    app_web = web.Application()
    app_web.router.add_post('/search', search_endpoint)
    app_web.router.add_post('/fetch', fetch_endpoint)
    app_web.router.add_post('/crawl', crawl_endpoint)
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
