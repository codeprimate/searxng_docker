# SearXNG Docker Compose Setup

This repository contains a complete Docker Compose configuration for running SearXNG, a privacy-respecting, open metasearch engine.

## Services Included

- **SearXNG**: The main search engine application
- **Redis**: In-memory database for caching search results
- **Caddy**: Reverse proxy with automatic HTTPS certificate management

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- A domain name (for production) or use localhost for testing

### 2. Configuration

Create a `.env` file in the project root with your configuration:

```bash
# Copy and edit the environment variables
cp .env.example .env
```

Edit the `.env` file with your values:

```env
# SearXNG Configuration
SEARXNG_HOSTNAME=your-domain.com  # or localhost for testing
SEARXNG_EMAIL=your-email@example.com  # for Let's Encrypt certificates
```

### 3. Generate Secret Key

Generate a secure secret key for SearXNG:

```bash
# On Linux/macOS
sed -i "s|ultrasecretkey|$(openssl rand -hex 32)|g" searxng/settings.yml

# On macOS (alternative)
sed -i '' "s|ultrasecretkey|$(openssl rand -hex 32)|g" searxng/settings.yml
```

### 4. Start the Services

```bash
# Start all services in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### 5. Access SearXNG

- **Local development**: http://localhost
- **Production**: https://your-domain.com

## Configuration Details

### SearXNG Settings

The SearXNG configuration is located in `searxng/settings.yml`. Key settings include:

- **Search engines**: Configured with popular engines like Google, Bing, DuckDuckGo, etc.
- **Privacy settings**: Safe search, autocomplete, and other privacy options
- **UI customization**: Theme, locale, and display options

### Caddy Configuration

The `Caddyfile` includes:

- Automatic HTTPS with Let's Encrypt
- Security headers (HSTS, CSP, etc.)
- Compression
- Request logging

### Redis Configuration

Redis is configured for:
- Data persistence with periodic saves
- Optimized logging level
- Network isolation

## Customization

### Adding Search Engines

Edit `searxng/settings.yml` to add or remove search engines:

```yaml
engines:
  - name: your_engine
    engine: your_engine
    shortcut: ye
    categories: general
    disabled: false
```

### Custom Themes

You can customize the UI by modifying the theme settings in `searxng/settings.yml`:

```yaml
ui:
  default_theme: "simple"
  theme_args:
    simple_style: "auto"
```

### Security Considerations

For production deployment:

1. **Change the secret key**: Always generate a new secret key
2. **Use HTTPS**: The Caddy configuration automatically handles this
3. **Firewall**: Only expose ports 80 and 443
4. **Updates**: Regularly update the Docker images
5. **Monitoring**: Consider adding monitoring and logging solutions

## Troubleshooting

### Common Issues

1. **Certificate issues**: Ensure your domain points to your server
2. **Port conflicts**: Make sure ports 80 and 443 are available
3. **Permission issues**: Check Docker volume permissions

### Logs

View logs for specific services:

```bash
# All services
docker compose logs

# Specific service
docker compose logs searxng
docker compose logs caddy
docker compose logs redis
```

### Reset Everything

To start fresh:

```bash
# Stop and remove containers, networks, and volumes
docker compose down -v

# Remove images (optional)
docker compose down --rmi all

# Start again
docker compose up -d
```

## Development

For development purposes, you can:

1. Mount local configuration files
2. Enable debug mode in `searxng/settings.yml`
3. Use localhost without HTTPS for testing

## License

This configuration is provided as-is. SearXNG itself is licensed under the GNU Affero General Public License v3.0.
