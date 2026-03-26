---
name: searxng-capabilities
description: >-
  SearXNG over MCP: one-query web search that merges results from multiple
  engines, plain-text page fetch,
  bounded multi-page crawls, and optional schema-based extraction. Suited to
  tasks that need live web search, reading or citing URLs, or structured
  data from pages through this integration.
---

# SearXNG: how to reason and call

## What you are working with

**SearXNG** is the metasearch backend (ranked links and snippets from many engines). A **separate MCP service** wraps the same ideas as **tools** (`search`, `fetch`, `crawl`, optional `extract`) and often mirrors them on HTTP. Those are **two different network endpoints** (different ports); do not assume one URL does everything.

Full parameter names, response fields, `curl` examples, limits, and env vars live in **[reference.md](reference.md)**. Read it when you need specifics; this file is the reasoning layer.

---

## Choose the capability before you call

Ask in order:

1. **Do you only need discovery (what exists on the web)?** → **`search`**.  
2. **Do you already have the canonical URL and need full readable text?** → **`fetch`**.  
3. **Do you need one index page and a small set of follow-on pages linked from it (e.g. doc hub)?** → **`crawl`** (only when link **anchor text** can be filtered; see reference).  
4. **Do you need one structured JSON object from a page, with a defined shape?** → **`extract`** only if the tool is actually listed on the MCP server (optional sidecar).

If the user gives a **URL** first, you usually **skip** search unless you still need more sources.

---

## How to reason about `search` results

- Treat titles and snippets as **pointers**, not proof. Engines aggregate third parties; snippets can be stale or wrong.  
- For anything that must be exact (quotes, numbers, legal/medical claims), **`fetch`** the chosen URL(s) and ground the answer in fetched text.  
- If results are thin, refine **query**, **`categories`**, **`engines`**, or **`time_range`** (exact knobs are in reference).  
- If the JSON mentions **`unresponsive_engines`**, partial failure is normal; say so instead of overstating coverage.

---

## How to call the MCP tools (discipline)

1. **List tools** on the SearXNG MCP server and confirm **`search`**, **`fetch`**, **`crawl`**, and whether **`extract`** exists.  
2. **Open the live JSON schema** for the tool you will call. Never invent argument names or types; schemas are the source of truth.  
3. **Call once** with minimal arguments, then widen (`max_results`, `pageno`, etc.) only if the first pass was insufficient.  
4. **Map HTTP errors** to user-visible messages: timeouts, 4xx/5xx, extract disabled, payload too large—see reference for typical cases.

`fetch` returns **plain text with HTML removed**, not raw HTML. Plan summarization and quoting accordingly.

---

## Composed workflows (patterns)

| Goal | Pattern |
|------|--------|
| Answer from the open web | `search` → pick 2–5 URLs → `fetch` each → synthesize with **citations** (URL per claim that needs grounding). |
| One site’s doc section | `crawl` from a sensible **seed** URL with **`filters`** that match how links are labeled; then summarize **subpages** returned. |
| Typed fields from a page | If `extract` exists: **`json_schema`** defines shape, optional **`prompt`** for rules. If not: `fetch` then structure output yourself. |

Avoid **`crawl`** when the user only needs one known URL—use **`fetch`**.

---

## Operator and limits

You cannot know exact numeric caps from memory. When the user hits truncation, rate limits, or missing **`extract`**, use **[reference.md](reference.md)** for default limits, env vars, and troubleshooting.
