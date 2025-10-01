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
- **Comprehensive documentation** - Step-by-step setup and maintenance guides

### API Integration

**SearXNG includes a powerful REST API** that allows you to integrate search functionality directly into your applications. This means you can:

- Build custom search interfaces
- Integrate search into existing applications
- Create automated search workflows
- Develop search-powered tools and services

The included Python query script (`searxng_search.py`) demonstrates how to use this API programmatically, making it easy to incorporate SearXNG's privacy-respecting search capabilities into your own projects.

Simply clone this repository, configure a few environment variables, and you'll have your own private search engine with full API access running in minutes.

## What's Included

- **SearXNG**: Main search application
- **Redis**: Caching for faster searches  
- **Query Script**: Python tool for programmatic searches

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

This is just an easy configuration to run SearXNG. Special thanks to:

- **[SearXNG](https://github.com/searxng/searxng)** - The privacy-respecting metasearch engine that powers this setup
- **[Docker](https://www.docker.com/)** - For containerization and easy deployment
- **[Redis](https://redis.io/)** - For caching and performance optimization

This configuration simplifies the deployment of SearXNG while maintaining its core privacy-focused features.