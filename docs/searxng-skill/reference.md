# SearXNG MCP — reference

Companion to `SKILL.md`. Parameter tables, HTTP details, examples, and limits—no reasoning guidance.

---

## Ports and roles

| Service | Role | Typical port |
|---------|------|----------------|
| **SearXNG** | Metasearch UI + `GET /search` | Often **7777** |
| **MCP server** | MCP tools + REST mirror | Often **7778** |

Configured via `SEARXNG_PORT`, `SEARXNG_MCP_PORT` (and protocol/host as deployed).

---

## Direct SearXNG: `GET /search`

**URL:** `{protocol}://{host}:{port}/search`

### Query parameters

| Parameter | Meaning | Examples |
|-----------|---------|----------|
| `q` | Query (**required**) | `python tutorial` |
| `format` | Response type | `json`, `html` |
| `categories` | Comma-separated | `general`, `it`, `videos`, `images`, `news`, `science`, `music`, `map`, `files`, `social media` |
| `engines` | Comma-separated engine ids | Instance-dependent: e.g. `google`, `bing`, `duckduckgo`, `wikipedia`, `github`, `stackexchange`, `reddit`, `youtube` |
| `lang` | Language | `en`, `es`, `fr`, `de` |

### Successful JSON (top level)

| Field | Meaning |
|-------|---------|
| `query` | Echoed query |
| `number_of_results` | Reported count |
| `results` | Hit list |
| `answers` | Direct answers (e.g. calculator) |
| `corrections` | Spelling corrections |
| `infoboxes` | Summary infoboxes |
| `suggestions` | Query suggestions |
| `unresponsive_engines` | Engines that failed |

### Typical `results[]` item

| Field | Meaning |
|-------|---------|
| `url`, `title`, `content` | Link, title, snippet |
| `engine` / `engines` | Source engine(s) |
| `parsed_url`, `template`, `positions`, `score` | Parsing / ranking metadata |

### Example

```bash
curl "http://localhost:7777/search?q=docker%20compose&format=json&categories=general,it"
```

---

## MCP HTTP mirror

Same behavior as MCP tools: **`POST`** JSON body to the MCP host/port.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/tools` | Tool list |
| POST | `/search` | Metasearch |
| POST | `/fetch` | URL → plain text |
| POST | `/crawl` | Seed + filtered subpages |
| POST | `/extract` | Structured extract (if enabled) |

### Search via HTTP

```bash
curl -s -X POST "http://localhost:7778/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"python 3.12 features","categories":"it","time_range":"month","pageno":1,"max_results":20}'
```

---

## MCP tool arguments (typical shapes)

Confirm names and types in the **live** tool schema on each server.

### `search`

| Argument | Required | Notes |
|----------|----------|------|
| `query` | Yes | Search string |
| `categories` | No | Comma-separated, e.g. `general,it,videos,images` |
| `engines` | No | Comma-separated engine ids |
| `language` | No | Often default `en` |
| `time_range` | No | Often `day`, `month`, `year` |
| `pageno` | No | Pagination (often starts at 1) |
| `max_results` | No | Default often 20; server caps (e.g. 100) |

### `fetch`

| Argument | Required | Notes |
|----------|----------|------|
| `url` | Yes | HTTP(S) URL |
| `headers` | No | Object of request headers |
| `max_content_length` | No | Character cap; hard max often ~1 MiB |

Returns **HTML-stripped plain text**.

### `crawl`

| Argument | Required | Notes |
|----------|----------|------|
| `url` | Yes | Seed page |
| `filters` | No | String array; substrings matched against **anchor text** of links |
| `headers` | No | Per-fetch headers |
| `subpage_limit` | No | Default often ~5; max often ~10 |
| `max_content_length` | No | Per-page character cap |

### `extract` (optional)

Requires operator enablement and a sidecar (`EXTRACT_ENABLED`, `EXTRACTOR_SIDECAR_URL`).

| Argument | Required | Notes |
|----------|----------|------|
| `url` | Yes | Page to fetch |
| `json_schema` | Yes | JSON Schema (supported subset) for output object |
| `prompt` | No | Natural-language extraction / disambiguation |
| `headers` | No | Fetch-step headers |

### Extract HTTP example

```bash
curl -s -X POST "http://localhost:7778/extract" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","json_schema":{"type":"object","properties":{"title":{"type":"string"}},"required":["title"]}}'
```

Typical HTTP issues: extract disabled (4xx + message), body too large (413), bad request (400), sidecar down (502).

---

## Defaults and limits (typical)

Order-of-magnitude; verify in server code if precision matters.

| Area | Typical |
|------|---------|
| `search` default results | ~20 |
| `search` max results | ~100 cap |
| `crawl` default subpages | ~5 |
| `crawl` max subpages | ~10 |
| `fetch` truncation | Often none by default; hard cap ~1 MiB chars/page |
| `extract` | Stricter content/body caps than fetch; timeout often ~120s |

---

## Environment variables (operators)

**SearXNG (backend):** `SEARXNG_PROTOCOL`, `SEARXNG_HOST`, `SEARXNG_PORT`

**MCP listen:** `SEARXNG_MCP_PORT`

**Extract:** `EXTRACT_ENABLED`, `EXTRACTOR_SIDECAR_URL`, optional `EXTRACT_TIMEOUT`, `EXTRACT_MAX_LENGTH`, `EXTRACT_MAX_JSON_BODY_BYTES`

---

## Troubleshooting

| Symptom | Things to check |
|---------|-------------------|
| Connection refused / timeout | Process up? Correct host/port? Firewall? |
| 404 on SearXNG | Base URL and path |
| Weak or empty search | Other `categories` / `engines`; inspect `unresponsive_engines` |
| `extract` missing or errors | `EXTRACT_ENABLED`, sidecar URL, size limits |
| MCP changes not visible | Restart Cursor / client after config edits |

---

## Installing the Cursor skill

Copy the skill directory so **`SKILL.md` sits at the folder root**:

| Scope | Path |
|-------|------|
| Project | `.cursor/skills/searxng-capabilities/` |
| User | `~/.cursor/skills/searxng-capabilities/` |

Restart Cursor or reload skills if changes do not apply.
