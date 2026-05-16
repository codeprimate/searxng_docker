# SearXNG Docker Stack

Self-hosted [SearXNG](https://github.com/searxng/searxng) metasearch with Redis caching, a Python query CLI, an MCP server for AI tools, and optional LLM-backed structured extraction. Clone, configure `.env`, run `docker compose up -d`, then search in the browser, from scripts, or through Cursor/Claude.

## Stack

| Service | Port (default) | Role |
|---------|----------------|------|
| **searxng** | 7777 | Web UI and native JSON search API |
| **redis** | internal | Result caching |
| **searxng-mcp** | 7778 | MCP tools + REST (`/search`, `/fetch`, `/crawl`, `/extract`) |
| **extractor-sidecar** | internal | LLM extraction for `/extract` (OpenRouter) |

## Quick start

### Prerequisites

- Docker and Docker Compose
- For **extract**: an [OpenRouter](https://openrouter.ai/) API key in `.env`

### Configure and run

```bash
cp env.example .env
# Edit .env: set SEARXNG_SECRET_KEY (see below) and OPENROUTER_API_KEY if using extract
openssl rand -hex 32   # paste into SEARXNG_SECRET_KEY
docker compose up -d
```

Minimum `.env` values:

```env
SEARXNG_PROTOCOL=http
SEARXNG_HOST=localhost
SEARXNG_PORT=7777
SEARXNG_BASE_URL=${SEARXNG_PROTOCOL}://${SEARXNG_HOST}:${SEARXNG_PORT}/
SEARXNG_SECRET_KEY=<from openssl rand -hex 32>
SEARXNG_MCP_PORT=7778
```

For structured extraction, keep `EXTRACT_ENABLED=true` (default in `env.example`) and set:

```env
OPENROUTER_API_KEY=sk-or-...
```

To disable the extract tool (search/fetch/crawl only), set `EXTRACT_ENABLED=false` in `.env`.

### Verify

```bash
docker compose ps
curl -sf "http://localhost:7777/search?q=test&format=json" | head -c 200
curl -sf http://localhost:7778/health
```

- **Search UI:** http://localhost:7777 (or your `SEARXNG_PORT`)
- **MCP HTTP:** http://localhost:7778

## Usage

Pick the interface that fits your workflow. All paths use the same private SearXNG instance.

### Web UI

Open the search URL in a browser. No extra setup beyond Quick start.

### SearXNG search API

Direct JSON search against SearXNG (no MCP):

```bash
curl "http://localhost:7777/search?q=python+docker&format=json"
curl "http://localhost:7777/search?q=docker&categories=general,it&format=json"
```

Response fields, engines, and error handling: [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

### Python: `searxng_search.py`

Command-line wrapper around the SearXNG API (stdlib only):

```bash
python searxng_search.py "your search term"
python searxng_search.py "docker" --categories general,it
python searxng_search.py "python" --output json
```

More flags and examples: [QUERY_SCRIPT_README.md](QUERY_SCRIPT_README.md).

### MCP server: tools and when to use them

The MCP server (`searxng-mcp`) exposes four capabilities. In agents, **`fetch`** returns full page text; **`extract`** fetches then returns JSON shaped by your schema and prompt—prefer **extract** on noisy pages when you want fields, not raw HTML.

| Tool | Use for |
|------|---------|
| **search** | Metasearch; categories, engines, time filters |
| **fetch** | Full cleaned page text to read or quote |
| **crawl** | Seed URL plus subpages whose link text matches filters |
| **extract** | Structured fields via LLM (`json_schema` + `prompt`); needs sidecar + API key |

**REST examples** (same host/port as health check):

```bash
# Search
curl -sS -X POST http://localhost:7778/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "categories": "general,it"}'

# Fetch page text
curl -sS -X POST http://localhost:7778/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Crawl related pages
curl -sS -X POST http://localhost:7778/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "filters": ["documentation"], "subpage_limit": 5}'

# Extract structured JSON (EXTRACT_ENABLED=true, OPENROUTER_API_KEY set)
curl -sS -X POST http://localhost:7778/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","json_schema":{"type":"object","properties":{"title":{"type":"string"}},"required":["title"]}}'
```

### Python: `extract_url.py`

CLI for `/extract` without hand-writing JSON Schema:

```bash
python extract_url.py "https://example.com/article" --keys title,author,summary

python extract_url.py "https://example.com/article" \
  --keys title,summary \
  --prompt "Main article only; ignore navigation and related links"

python extract_url.py "https://example.com/article" \
  --json '{"title":"Page title","summary":"Two-sentence summary"}'
```

Stdout is the extracted `data` object (indented JSON). Optional env: `SEARXNG_MCP_HOST`, `SEARXNG_MCP_PORT` (default `localhost:7778`), `EXTRACT_TIMEOUT` (default `120`).

### Cursor and Claude

**1. Point the client at the MCP container** (`~/.cursor/mcp.json` or Claude Desktop config):

```json
{
  "mcpServers": {
    "searxng": {
      "command": "docker",
      "args": ["exec", "-i", "searxng-mcp", "python", "server.py"],
      "description": "Private SearXNG: search, fetch, crawl, extract"
    }
  }
}
```

Claude Desktop paths: macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows `%APPDATA%\Claude\claude_desktop_config.json`. Restart the app after editing.

**2. Install the agent skill (Cursor, recommended)** so the model knows when to use `extract` vs `fetch` and how to design schemas:

```bash
cp -r docs/searxng-skill ~/.cursor/skills/searxng-capabilities
```

Reload Cursor. Workflows: [docs/searxng-skill/SKILL.md](docs/searxng-skill/SKILL.md).

MCP implementation details: [mcp-server/README.md](mcp-server/README.md). Extract pipeline: [extractor-sidecar/README.md](extractor-sidecar/README.md), [docs/extract-sidecar-specification.md](docs/extract-sidecar-specification.md).

## Operations

Services use `restart: unless-stopped`. Redis data lives in a Docker volume; SearXNG config in `./searxng/`.

```bash
docker compose ps
docker compose logs --tail=50
docker compose pull && docker compose up -d   # update images
```

Logs rotate at 1MB per container. Tune engines in `searxng/settings.yml` if needed.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Services won't start | `docker compose logs` then `docker compose down && docker compose up -d` |
| Can't reach search UI | `docker compose ps`, `SEARXNG_PORT`, firewall |
| MCP connection refused | `docker compose ps searxng-mcp`, `SEARXNG_MCP_PORT` conflicts |
| Extract fails | `OPENROUTER_API_KEY`, `EXTRACT_ENABLED=true`, `docker compose ps extractor-sidecar` |
| AI client ignores MCP | Restart Cursor/Claude after config change |

Full reset (removes volumes):

```bash
docker compose down -v && docker compose up -d
```

## Documentation

| Doc | Contents |
|-----|----------|
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Native SearXNG API schema and curl |
| [QUERY_SCRIPT_README.md](QUERY_SCRIPT_README.md) | `searxng_search.py` options |
| [mcp-server/README.md](mcp-server/README.md) | MCP server design and endpoints |
| [extractor-sidecar/README.md](extractor-sidecar/README.md) | Sidecar env and caching |
| [docs/searxng-skill/](docs/searxng-skill/) | Agent workflows for search/fetch/crawl/extract |

## Acknowledgments

Built on [SearXNG](https://github.com/searxng/searxng), [Docker](https://www.docker.com/), [Redis](https://redis.io/), and the [Model Context Protocol](https://modelcontextprotocol.io/).
