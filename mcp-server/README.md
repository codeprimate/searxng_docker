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
  -d '{"query": "python programming", "categories": "general,it"}'
```

### Fetch
```bash
curl -X POST http://localhost:${SEARXNG_MCP_PORT}/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "headers": {"Accept": "application/json"}}'
```

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
          "web_fetch"
        ],
        "usageHints": {
          "whenToUse": "Use when you need current information, recent events, web search results, or to fetch content from specific URLs that aren't in your training data",
          "howToUse": "Call the 'search' tool with a query string for metasearch, or the 'fetch' tool with a URL to retrieve specific content. Optionally specify categories (general,it,news,science,images) and language (default: en) for search, or custom headers for fetch",
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
        "web_fetch"
      ],
      "usageHints": {
        "whenToUse": "Use when you need current information, recent events, web search results, or to fetch content from specific URLs that aren't in your training data",
        "howToUse": "Call the 'search' tool with a query string for metasearch, or the 'fetch' tool with a URL to retrieve specific content. Optionally specify categories (general,it,news,science,images) and language (default: en) for search, or custom headers for fetch",
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
  -d '{"query": "python programming", "categories": "general,it"}'

# Fetch endpoint  
curl -X POST http://localhost:7778/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "headers": {"Accept": "application/json"}}'
```


### Troubleshooting

- **Connection issues**: Ensure SearXNG is running and accessible at `SEARXNG_URL`
- **Port conflicts**: Change `SEARXNG_MCP_PORT` if 7778 is already in use
- **Docker networking**: Use `--network=host` or ensure proper port mapping
- **Cursor restart**: Restart Cursor after adding MCP server configuration
