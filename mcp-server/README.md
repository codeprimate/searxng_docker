# SearXNG MCP Server

Minimal MCP server for SearXNG search engine integration with Cursor and Claude.

## Usage

## Environment Variables

Make sure to set the following environment variables:

```bash
# Required
SEARXNG_PROTOCOL=${SEARXNG_PROTOCOL}
SEARXNG_HOST=searxng
SEARXNG_PORT=${SEARXNG_PORT}
```

## Configuration

The MCP server now supports configurable limits with centralized constants:

### Default Limits
- **Search Results**: 20 results (configurable up to 100)
- **Crawl Subpages**: 10 subpages (configurable up to 20)
- **Content Length**: No truncation by default (configurable up to 1MB per page)

### Safety Limits
- **Maximum Search Results**: 100
- **Maximum Subpages**: 20
- **Maximum Content Length**: 1MB per page
- **Maximum Search Snippet**: 10k characters

These limits can be adjusted by modifying the constants in `server.py` if needed.

### Start with Docker Compose
```bash
docker compose up -d
```

The MCP server will be available at `http://localhost:${SEARXNG_MCP_PORT}` (default: 7778)

## Web API Endpoints

### Search
```bash
curl -X POST http://localhost:${SEARXNG_MCP_PORT}/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "categories": "general,it", "time_range": "month", "pageno": 1, "max_results": 20}'
```

**Search Parameters:**
- `query` (required): The search query
- `categories` (optional): Comma-separated categories (general,it,videos,images)
- `engines` (optional): Comma-separated search engines (bing,duckduckgo,google,startpage,wikipedia,github,reddit,youtube,stackexchange,etc.)
- `language` (optional): Language code (default: en)
- `time_range` (optional): Time range for search results (day, month, year)
- `pageno` (optional): Page number for pagination (default: 1)
- `max_results` (optional): Maximum number of results to return (default: 20, max: 100)

**Note:** Safe search is always disabled (safesearch=0) for maximum search results.

### Fetch
```bash
curl -X POST http://localhost:${SEARXNG_MCP_PORT}/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "headers": {"Accept": "application/json"}, "max_content_length": 50000}'
```

**Fetch Parameters:**
- `url` (required): The URL to fetch content from
- `headers` (optional): Custom headers as key-value pairs
- `max_content_length` (optional): Maximum content length in characters (default: no limit, max: 1MB)

### Crawl
```bash
curl -X POST http://localhost:${SEARXNG_MCP_PORT}/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "filters": ["documentation", "guide"], "headers": {"Accept": "text/html"}, "subpage_limit": 10, "max_content_length": 10000}'
```

**Crawl Parameters:**
- `url` (required): The URL to crawl
- `filters` (optional): Array of strings to filter anchor text (at least one must match)
- `headers` (optional): Custom headers as key-value pairs
- `subpage_limit` (optional): Maximum number of subpages to crawl (default: 10, max: 20)
- `max_content_length` (optional): Maximum content length per page in characters (default: no limit, max: 1MB)

### Health Check
```bash
curl http://localhost:${SEARXNG_MCP_PORT}/health
```

### Available Tools
```bash
curl http://localhost:${SEARXNG_MCP_PORT}/tools
```

## Claude Integration

### Claude Desktop Configuration

To use this MCP server with Claude Desktop, add the following configuration to your Claude Desktop settings:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "searxng": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "searxng-mcp",
        "python",
        "server.py"
      ],
      "description": "SearXNG metasearch engine that aggregates results from various search services",
        "capabilities": [
          "web_search",
          "web_fetch",
          "web_crawl"
        ],
        "usageHints": {
          "whenToUse": "Use when you need current information, recent events, web search results, or to fetch content from specific URLs that aren't in your training data",
          "howToUse": "Call the 'search' tool with a query string for metasearch, the 'fetch' tool with a URL to retrieve specific content, or the 'crawl' tool to explore a website and its related pages. For search, optionally specify categories (general,it,videos,images), engines, language (default: en), time_range (day/month/year), pageno (default: 1), and max_results (default: 20). For fetch, use custom headers and max_content_length. For crawl, use filters, subpage_limit (default: 10), and max_content_length.",
        "examples": [
          {
            "userQuery": "What are the latest Python 3.12 features?",
            "agentAction": "Use the 'search' tool with query 'Python 3.12 new features' and categories 'it'"
          },
          {
            "userQuery": "Find recent news about renewable energy",
            "agentAction": "Use the 'search' tool with query 'renewable energy news' and categories 'news'"
          },
          {
            "userQuery": "Search for Docker best practices",
            "agentAction": "Use the 'search' tool with query 'Docker best practices' and categories 'it'"
          },
          {
            "userQuery": "Explore the documentation on a website",
            "agentAction": "Use the 'crawl' tool with the website URL and filters like ['documentation', 'guide', 'tutorial']"
          }
        ]
      }
    }
  }
}
```

## Cursor Integration

### MCP Server Configuration

To use this MCP server with Cursor, add the following configuration to your Cursor MCP settings:

**Configuration file**: `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "searxng": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "searxng-mcp",
        "python",
        "server.py"
      ],
      "description": "SearXNG metasearch engine that aggregates results from various search services",
      "capabilities": [
        "web_search",
        "web_fetch",
        "web_crawl"
      ],
      "usageHints": {
        "whenToUse": "Use when you need current information, recent events, web search results, or to fetch content from specific URLs that aren't in your training data",
        "howToUse": "Call the 'search' tool with a query string for metasearch, the 'fetch' tool with a URL to retrieve specific content, or the 'crawl' tool to explore a website and its related pages. For search, optionally specify categories (general,it,videos,images), engines, language (default: en), time_range (day/month/year), pageno (default: 1), and max_results (default: 20). For fetch, use custom headers and max_content_length. For crawl, use filters, subpage_limit (default: 10), and max_content_length.",
        "examples": [
          {
            "userQuery": "What are the latest Python 3.12 features?",
            "agentAction": "Use the 'search' tool with query 'Python 3.12 new features' and categories 'it'"
          },
          {
            "userQuery": "Find recent news about renewable energy",
            "agentAction": "Use the 'search' tool with query 'renewable energy news' and categories 'news'"
          },
          {
            "userQuery": "Search for Docker best practices",
            "agentAction": "Use the 'search' tool with query 'Docker best practices' and categories 'it'"
          },
          {
            "userQuery": "Explore the documentation on a website",
            "agentAction": "Use the 'crawl' tool with the website URL and filters like ['documentation', 'guide', 'tutorial']"
          }
        ]
      }
    }
  }
}
```

### Web API Integration (Alternative)

For web-based integration with Cursor, you can also use the HTTP endpoints directly:

```bash
# Search endpoint
curl -X POST http://localhost:7778/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "categories": "general,it", "time_range": "month", "pageno": 1}'

# Fetch endpoint  
curl -X POST http://localhost:7778/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "headers": {"Accept": "application/json"}}'

# Crawl endpoint
curl -X POST http://localhost:7778/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "filters": ["documentation", "guide"], "headers": {"Accept": "text/html"}, "subpage_limit": 10, "max_content_length": 10000}'
```


### Troubleshooting

- **Connection issues**: Ensure SearXNG is running and accessible at `SEARXNG_URL`
- **Port conflicts**: Change `SEARXNG_MCP_PORT` if 7778 is already in use
- **Docker networking**: Use `--network=host` or ensure proper port mapping
- **Cursor restart**: Restart Cursor after adding MCP server configuration
