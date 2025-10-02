# SearXNG Search Engine

## What is SearXNG?

**SearXNG** is a free internet metasearch engine that aggregates results from more than 70 search services. It's designed to be privacy-respecting, meaning it doesn't track users or store personal data. Unlike traditional search engines, SearXNG:

- **Protects Privacy**: No user tracking, no personal data collection
- **Aggregates Results**: Combines results from multiple search engines (Google, Bing, DuckDuckGo, etc.)
- **Open Source**: Fully transparent and community-driven
- **Self-hostable**: Run your own search engine instance
- **Customizable**: Configure which search engines to use and how results are displayed

## What This Repository Provides

This repository contains a **ready-to-deploy SearXNG configuration** that makes it easy to run your own private search engine. Instead of manually configuring SearXNG, this setup provides:

- **Docker-based deployment** - Everything runs in containers for easy setup
- **Redis caching** - Faster search results through intelligent caching
- **Production-ready configuration** - Optimized settings for real-world use
- **Query script** - Python tool for programmatic searches
- **MCP Server** - Model Context Protocol server for AI integration with Cursor and Claude
- **Comprehensive documentation** - Step-by-step setup and maintenance guides

### API Integration

**SearXNG includes a powerful REST API** that allows you to integrate search functionality directly into your applications. This means you can:

- Build custom search interfaces
- Integrate search into existing applications
- Create automated search workflows
- Develop search-powered tools and services

The included Python query script (`searxng_search.py`) demonstrates how to use this API programmatically, making it easy to incorporate SearXNG's privacy-respecting search capabilities into your own projects.

### MCP Server Integration

**This repository includes a powerful MCP (Model Context Protocol) server** that enables seamless integration with AI development tools like Cursor and Claude. The MCP server provides:

- **AI-Powered Search**: Direct search integration with AI assistants
- **Web Content Fetching**: Retrieve and parse web content for AI analysis
- **Intelligent Crawling**: Explore websites and extract relevant information
- **Privacy-First**: All searches go through your private SearXNG instance
- **Multiple Interfaces**: Both MCP protocol and REST API endpoints

The MCP server runs as a separate container and provides three powerful tools:
- **Search**: Metasearch across multiple engines with category filtering
- **Fetch**: Retrieve and clean web content from any URL
- **Crawl**: Explore websites and extract content from related pages

This makes it easy to give AI assistants access to current, real-time information while maintaining complete privacy and control over your search data.

Simply clone this repository, configure a few environment variables, and you'll have your own private search engine with full API access and AI integration running in minutes.

## What's Included

- **SearXNG**: Main search application
- **Redis**: Caching for faster searches  
- **Query Script**: Python tool for programmatic searches
- **MCP Server**: Model Context Protocol server for AI integration

## Quick Setup

### 1. Prerequisites
- Docker and Docker Compose
- Domain name (for production) or use localhost

### 2. Configure Environment
```bash
# Copy environment template
cp env.example .env

# Edit with your values
nano .env
```

Required settings in `.env`:
```env
SEARXNG_PROTOCOL=http
SEARXNG_HOST=localhost
SEARXNG_PORT=7777
SEARXNG_BASE_URL=${SEARXNG_PROTOCOL}://${SEARXNG_HOST}:${SEARXNG_PORT}/
SEARXNG_SECRET_KEY=your-secret-key-here
```

### 3. Generate Secret Key
```bash
# Generate secure key
openssl rand -hex 32
```
Copy the output to `SEARXNG_SECRET_KEY` in your `.env` file.

### 4. Start Services
```bash
# Start all services
docker compose up -d
```

### 5. Access Search Engine
- **Local**: http://localhost:7777 (or your configured SEARXNG_PORT)
- **Production**: https://your-domain.com

## Running as a Service

### Auto-restart
Services automatically restart on failure (`restart: unless-stopped`)

### Data Persistence
- Redis data persists in Docker volume
- SearXNG configuration persists in `./searxng/` directory

### Monitoring
```bash
# Check service health
docker compose ps

# View recent logs
docker compose logs --tail=50

# Monitor resource usage
docker stats
```

### Updates
```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d
```

## Using the Query Script

Search programmatically with the included Python script:

```bash
# Basic search
python searxng_search.py "your search term"

# Search specific categories
python searxng_search.py "docker" --categories general,it

# Get JSON output
python searxng_search.py "python" --output json
```

See `QUERY_SCRIPT_README.md` for detailed usage.

## MCP Server Setup and Usage

The MCP server provides AI integration capabilities for Cursor and Claude, enabling them to perform web searches and fetch content through your private SearXNG instance.

### Environment Configuration

The MCP server uses the same environment variables as the main setup, with one additional variable:

```env
# Add to your .env file
SEARXNG_MCP_PORT=7778
```

### Starting the MCP Server

The MCP server starts automatically with the main services:

```bash
# Start all services including MCP server
docker compose up -d

# Check MCP server status
docker compose ps searxng-mcp
```

The MCP server will be available at `http://localhost:7778` (or your configured `SEARXNG_MCP_PORT`).

### Cursor Integration

To use the MCP server with Cursor, add this configuration to `~/.cursor/mcp.json`:

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
      ]
    }
  }
}
```

### Claude Desktop Integration

For Claude Desktop, add this configuration to your Claude Desktop settings:

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
      "description": "SearXNG metasearch engine that aggregates results from various search services"
    }
  }
}
```

### Web API Usage

You can also use the MCP server's REST API directly:

```bash
# Search
curl -X POST http://localhost:7778/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "categories": "general,it"}'

# Fetch content
curl -X POST http://localhost:7778/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Crawl website
curl -X POST http://localhost:7778/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "filters": ["documentation", "guide"], "subpage_limit": 5}'

# Health check
curl http://localhost:7778/health
```

### Available Tools

The MCP server provides three main tools:

1. **Search Tool**: Perform metasearch queries with optional category filtering
2. **Fetch Tool**: Retrieve and clean content from any URL
3. **Crawl Tool**: Explore websites and extract content from related pages

For detailed API documentation, see the [MCP Server README](mcp-server/README.md).

## Troubleshooting

### Services Won't Start
```bash
# Check logs
docker compose logs

# Restart everything
docker compose down && docker compose up -d
```

### Can't Access Search
- Verify your configured port (SEARXNG_PORT) is open
- Check environment variables match your setup
- Ensure services are running: `docker compose ps`

### MCP Server Issues
- **MCP server not responding**: Check if container is running: `docker compose ps searxng-mcp`
- **Connection refused**: Verify `SEARXNG_MCP_PORT` is not conflicting with other services
- **AI integration not working**: Restart Cursor/Claude after adding MCP configuration
- **Search failures**: Ensure SearXNG container is healthy: `docker compose ps searxng`

### Reset Everything
```bash
# Stop and remove all data
docker compose down -v

# Start fresh
docker compose up -d
```

## Maintenance

### Regular Tasks
- Update Docker images monthly
- Monitor disk space for Redis data
- Check logs for errors

### Log Management
Logs are automatically rotated (1MB max, 1 file kept)

### Performance
- Adjust search engines in `searxng/settings.yml` if needed

## Acknowledgments

This is just an easy configuration to run SearXNG with AI integration capabilities. Special thanks to:

- **[SearXNG](https://github.com/searxng/searxng)** - The privacy-respecting metasearch engine that powers this setup
- **[Docker](https://www.docker.com/)** - For containerization and easy deployment
- **[Redis](https://redis.io/)** - For caching and performance optimization
- **[Model Context Protocol](https://modelcontextprotocol.io/)** - For enabling AI integration with development tools

This configuration simplifies the deployment of SearXNG while maintaining its core privacy-focused features and adding powerful AI integration capabilities through the MCP server.