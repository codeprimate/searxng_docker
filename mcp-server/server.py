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

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Web server imports
from aiohttp import web, web_request

# Configuration
DEFAULT_TIMEOUT = 30
DEFAULT_USER_AGENT = "SearXNG-MCP-Server/1.0"

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
        """Fetch content from a URL"""
        try:
            request = urllib.request.Request(url)
            request.add_header('User-Agent', DEFAULT_USER_AGENT)
            
            # Add custom headers if provided
            if headers:
                for key, value in headers.items():
                    request.add_header(key, value)
            
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content = response.read().decode('utf-8')
                return {
                    'url': url,
                    'status_code': response.status,
                    'headers': dict(response.headers),
                    'content': content,
                    'content_length': len(content)
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
            description="Fetch content from a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch content from"},
                    "headers": {"type": "object", "description": "Optional custom headers as key-value pairs"}
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
            
            if content and len(content) > 200:
                content = content[:200] + "..."
            
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
        response += f"Content Length: {result['content_length']} characters\n\n"
        
        # Truncate content if too long
        content = result['content']
        if len(content) > 1000:
            content = content[:1000] + "...\n[Content truncated]"
        
        response += f"Content:\n{content}"
        
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
            "description": "Fetch content from a URL provided by SearXNG metasearch engine",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch content from"},
                    "headers": {"type": "object", "description": "Optional custom headers as key-value pairs"}
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
