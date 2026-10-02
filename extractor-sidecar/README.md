# Extractor sidecar

Node HTTP service for LLM-backed structured extraction (`POST /extract`) using `@lightfeed/extractor`, LangChain `ChatOpenAI` against OpenRouter, optional Redis caching, and a hand-rolled JSON Schema subset → Zod layer.

- **Port**: `3000` (see `PORT`)
- **Health**: `GET /health` → `{ "status": "ok" }`
- **Config**: see `.env.example`

Build and run locally:

```bash
npm ci
npm run build
npm start
```

Tests: `npm test`

## Hollow-result guard

The extractor prompt tells the model to leave fields empty when uncertain, so a
stalled reasoning model can return a well-shaped all-empty payload. Since
2026-10-02 such a result is retried once and, if still hollow, returned as HTTP
502 (`extraction failed: model returned an empty result twice (not cached)`) —
never cached. Trade-off: a page that genuinely contains nothing matching the
schema now also reports 502 instead of an empty payload; reframe the query.

Docker: multi-stage build in `Dockerfile` (matches Compose service `extractor-sidecar`).
