---
name: searxng-capabilities
description: >-
  SearXNG over MCP: metasearch, plain-text fetch, bounded crawls, and
  LLM-backed extract (json_schema + prompt). Use for live web research,
  grounded citations, and structured answers from noisy pages—not raw HTML dumps.
---

# SearXNG MCP — how to reason and call

## What you are working with

**SearXNG** aggregates search results (metasearch). A **separate MCP server** exposes tools—`search`, `fetch`, `crawl`, and optionally **`extract`**—on a different port than the SearXNG UI. Do not conflate the two base URLs.

Use the **SearXNG MCP server** for live web tasks. Parameters, limits, `curl` examples, and env vars: **[reference.md](reference.md)**.

---

## `fetch` vs `extract` (decide first)

| Tool | Use when |
|------|----------|
| **`fetch`** | You need **full page text**—verbatim quotes, long prose, or your own multi-step reasoning on the whole document. |
| **`extract`** | You want the **answer**, not the page. The server fetches stripped HTML, then an **LLM** returns one JSON object matching your schema. |

`extract` = fetch + **LLM preprocessing**. Treat **`json_schema` + `prompt` as one contract**:

- **Schema** — shape of the output (`required` keys, types, arrays, enums).
- **Prompt** — semantics the schema cannot express: what to ignore, caps, normalization, “main article only”, tie-breakers, date formats.

**Prefer `extract`** on noisy pages (homepages, listings, docs with nav) and when judgment is needed (real headlines vs sidebar, current price, top N relevant items, short summary).

**Prefer `fetch`** when exact wording matters, the document is long and you will reason across it yourself, or `extract` is disabled or keeps returning bad shapes after retries.

Confirm `extract` exists on the MCP server before calling it (`EXTRACT_ENABLED` + extractor sidecar).

---

## Choose a tool

| Need | Tool |
|------|------|
| Find URLs | `search` |
| Structured or semantic output from URL(s) | `extract` |
| Hub + linked pages (filter **anchor text**) | `crawl` |
| Raw full text | `fetch` |

**Decision order:** discovery → `search`; known URL + answer shape → `extract`; known URL + full read → `fetch`; hub + related links → `crawl` then `extract` or `fetch` per page.

Skip `search` when the user already gave the URL (unless you need more sources). Do not `crawl` a single article—`extract` or `fetch` it.

---

## Default flow

1. `search` → pick the best URL(s). Snippets are pointers only.
2. **`extract`** per URL with a schema shaped to the user’s goal (or **`fetch`** when they need full prose).
3. Cite URLs for grounded claims.

**Crawl + extract:** `crawl` scopes related pages → **`extract` each** with the same schema + prompt when comparing sites or doc sections.

---

## `search` discipline

- Ground exact claims with **`fetch` or `extract`** on chosen URLs, not snippets alone.
- Refine `query`, `categories`, `engines`, or `time_range` if results are thin (see reference).
- Mention **`unresponsive_engines`** when present—coverage may be partial.

---

## Use `extract` intelligently

Match the schema to the deliverable—not only flat field lists:

| Goal | Schema sketch |
|------|----------------|
| Facts | `{ "price", "currency", "in_stock" }`, `{ "author", "published_at" }` |
| Lists | `{ "items": [{ "title", "url", "summary" }] }`, tables as row arrays |
| Synthesis | `{ "summary", "key_points": ["string"] }`, `{ "pros", "cons" }` |
| Classification | enums, e.g. `"sentiment": "positive" \| "negative" \| "neutral"` |
| Cross-page compare | **Same** schema + prompt on each URL after `search` or `crawl` |

**Prompt:** exclude ads, nav, shopping, games, duplicate video cards; set max items; note subscriber-only gaps; specify units, locales, and tie-breakers (“official spec only”).

**Schema:** use `["string","null"]` when a field may be absent; keep objects flat when possible; nest when natural. Read the live tool schema for the supported JSON Schema subset.

Re-run with a tighter schema or prompt before falling back—bad shape is often fixable, not a dead end.

---

## `crawl` discipline

- `filters` match **link anchor text**, not URL paths.
- Keep `subpage_limit` low (3–5) unless the first pass is incomplete.
- Follow with **`extract` each** subpage (same schema) when comparing sections or products.

---

## Composed workflows

| Goal | Pattern |
|------|---------|
| Web answer with citations | `search` → 2–5 URLs → `extract` (or `fetch` if prose-heavy) → cite URLs |
| Headlines / tables / specs | `search` or known URL → `extract` with list/object schema + exclusion prompt |
| Doc hub on one site | `crawl` (seed + `filters`) → `extract` or `fetch` per subpage |
| Open-ended read one article | `fetch` only |

---

## Calling discipline

1. List MCP tools; open the **live JSON schema** for the tool you call—never invent argument names.
2. Call once with minimal args; widen (`max_results`, `pageno`, …) only if needed.
3. Map errors clearly: timeout, 4xx/5xx, extract disabled, payload too large (see reference).

`fetch` returns HTML-stripped **plain text**, not raw HTML.

---

## Fallback when SearXNG fails or quality is poor

If tools **error** (timeout, 4xx/5xx, extract disabled) or **`extract`/`fetch` quality is poor** (empty, wrong page, schema garbage, obvious mismatch after retry):

1. State briefly that SearXNG was insufficient.
2. Use **builtin** `WebSearch` + `WebFetch` (Defuddle skill for articles).
3. Structure output yourself if `extract` is unavailable.

Do not loop identical SearXNG calls—change URL, query, schema, or prompt.

---

## Limits and operators

Numeric caps and troubleshooting: **[reference.md](reference.md)**.
