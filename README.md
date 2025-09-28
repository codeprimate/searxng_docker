# SearXNG Search Engine

A privacy-respecting search engine that aggregates results from multiple sources.
(this version has been modified)

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
SEARXNG_SECRET_KEY=your-secret-key-here
SEARXNG_BASE_URL=http://localhost:7777/
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

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5. Access Search Engine
- **Local**: http://localhost:7777
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

## Production Deployment

### Domain Setup
1. Point your domain to your server
2. Update `SEARXNG_BASE_URL` in `.env` to use your domain
3. Ensure ports 80/443 are open

### Security
- Change the default secret key
- Use HTTPS (automatic with proper domain setup)
- Keep Docker images updated

### Backup
```bash
# Backup configuration
tar -czf searxng-backup.tar.gz searxng/ .env

# Backup Redis data
docker compose exec redis redis-cli BGSAVE
```

## Troubleshooting

### Services Won't Start
```bash
# Check logs
docker compose logs

# Restart everything
docker compose down && docker compose up -d
```

### Can't Access Search
- Verify port 7777 is open
- Check `SEARXNG_BASE_URL` matches your setup
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
- Redis caching improves response times
- Adjust search engines in `searxng/settings.yml` if needed