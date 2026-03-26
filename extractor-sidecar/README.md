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

Docker: multi-stage build in `Dockerfile` (matches Compose service `extractor-sidecar`).
