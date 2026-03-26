# Implementation TODO: MCP `extract` + Node extractor sidecar

## Specification Reference

**Source Document**: [docs/extract-sidecar-specification.md](../docs/extract-sidecar-specification.md)

*This specification document must be loaded alongside this plan during execution to provide complete context and requirements.*

## Implementation decisions (prescriptive)

The following choices are **locked** for v1. Do not revisit without updating this document and the specification.

| Topic | Decision |
|-------|----------|
| Sidecar stack | **TypeScript**, **Express** for HTTP, **`npm`** + **`package-lock.json`**, Node **LTS** (align `engines` in `package.json`). |
| Sidecar listen port | **3000** internally; Compose maps only if needed. |
| Redis client | **`ioredis`**. |
| Redis URL / DB | **`redis://redis:6379/1`** in Compose (logical DB **1** for `extract:` keys per isolation recommendation). |
| Redis connect mode | **Lazy connect** on first cache operation; log warnings; never fail a request solely because Redis is down when cache is enabled. |
| `EXTRACT_CACHE_ENABLED` default | **`true`** when `REDIS_URL` is set; **`false`** when unset. |
| JSON Schema nullable (v1) | Support **`type: ["T", "null"]`** only for nullable fields; **do not** support a separate `nullable: true` keyword in v1 (reject or ignore—**reject** with 400 if present to keep surface small). |
| Object strictness | For `type: "object"`, treat as **strict**: no extra keys in data—Zod **`.strict()`**; reject schemas with **`additionalProperties: true`**; if **`additionalProperties` is omitted**, treat as **`false`** (strict object). |
| Schema→Zod implementation | **Hand-rolled** recursive builder for the supported subset only (no full Draft-2020-12 library unless it can be constrained to this subset). |
| `EXTRACT_MAX_LENGTH` handling | **Reject** (do not truncate for v1): if `content` length exceeds the limit after normalization, return **413** with a clear message (spec: reject with clear error). |
| Raw POST body size (MCP and sidecar) | Default **`EXTRACT_MAX_JSON_BODY_BYTES=2097152`** (2 MiB); reject with **413** if exceeded before JSON parse. |
| Oversize / limits HTTP codes | **413** for any over-limit payload: raw body over **`EXTRACT_MAX_JSON_BODY_BYTES`**, or **`content`** over **`EXTRACT_MAX_LENGTH`**. **400** for invalid JSON, invalid arguments, empty/whitespace-only content, schema conversion failure, unsupported schema keywords. |
| Sidecar→OpenRouter timeout | **`EXTRACT_OPENROUTER_TIMEOUT_MS` default `115000`** (115s) so OpenRouter fails before MCP **`EXTRACT_TIMEOUT`** (120s) elapses on the same request (spec: predictable ordering). |
| Cache hit response | Include **`cached: true`**; **omit `usage`** on cache hits (or set numeric token fields to **0**—pick **omit `usage`** on hits for clarity). |
| MCP→sidecar errors (HTTP mirror) | **502** when the sidecar cannot be reached or returns a non-success that maps to “bad gateway” (connection errors, invalid gateway response). **504** optional for MCP timeout—if not implemented, surface timeout as **502** with message. |
| `POST /extract` when disabled | **404** + stable JSON body (already locked in Phase 3). |
| MCP stdio tool (no HTTP) | Over-limit and **400**-class failures: **`TextContent`** with clear error strings; mirror the **same messages** as HTTP JSON `error` fields where practical. |
| Compose: `searxng-mcp` → sidecar | **No** `depends_on: extractor-sidecar` for MCP (sidecar may start later; clients retry or see **502** until healthy). Sidecar **`depends_on: redis`** (optional: `condition: service_started` only—no strict Redis health gate required for v1). |
| Example `.env` / Compose | Ship **`EXTRACT_ENABLED=true`** in the **documented full-stack example**; keep opt-out documented for minimal stacks. |
| Tests | **`pytest`** under `mcp-server/tests/`; **`vitest`** in `extractor-sidecar`. |
| Tool list source of truth | **Single Python function** (e.g. `build_tool_definitions(extract_enabled: bool)`) feeding both **`list_tools`** and **`tools_endpoint`**. |

## Overview

- **Complexity**: Complex (new Node service, LLM integration, Redis cache, MCP + HTTP surfaces, JSON Schema subset layer)
- **Risk Level**: Medium (external OpenRouter dependency, schema↔Zod correctness, Redis operational tuning)
- **Key Dependencies**: `@lightfeed/extractor`, `@langchain/openai`, `zod`, Redis (`redis` service on `searxng` network), existing `SearXNGClient.fetch` in `mcp-server/server.py`
- **Estimated Effort**: Multi-day (sidecar + MCP + Compose + tests + docs)
- **Specification Sections**: Problem Statement, Functional Requirements, Technical Constraints, Caching, Edge Cases, Technical Approach, JSON Schema subset, Acceptance Criteria, Implementation Tasks, Risk Assessment

## Phase Strategy

Work proceeds in five phases so each milestone is testable on its own:

1. **Sidecar core (no Redis):** A containerized Node HTTP service with `GET /health`, `POST /extract` using OpenRouter + `@lightfeed/extractor`, JSON Schema subset validation, and Zod generation—proves the extraction pipeline before caching or MCP wiring.
2. **Sidecar caching:** Redis-backed LLM result cache with deterministic keys, TTL, graceful degradation, and `cached` in responses—matches § Caching without changing MCP yet (validate with direct HTTP + Redis).
3. **MCP integration:** `EXTRACT_ENABLED` gating, conditional `list_tools` / `call_tool`, shared fetch path with `fetch`, sidecar HTTP client with separate timeouts/limits, **`POST /extract`** HTTP mirror (spec: recommended parity with `/search`, `/fetch`) and `tools` list parity.
4. **Compose & documentation:** New service on `searxng`, env wiring for MCP and sidecar, README and API docs; optional Redis tuning notes as deployment recommendations.
5. **Automated tests:** Introduce test tooling if absent; unit tests for schema conversion and cache keys; integration tests with mocked OpenRouter and Redis; MCP tests with mocked sidecar.

## Progress Indicators

- 📋 **Planned** - Not started
- 🔄 **In Progress** - Currently being worked on
- ✅ **Completed** - Successfully finished
- ❌ **Blocked/Failed** - Encountered issues or dependencies
- ⏸️ **Paused** - Temporarily suspended
- 🔍 **Under Review** - Completed but needs validation

*Progress indicators appear at the end of phase, task, and subtask headings as: `- 📋 Planned`*

---

## Implementation Phases

## Phase 1: Extractor sidecar (Node) — core HTTP API and LLM extraction - 📋 Planned

*Incremental Goal: `extractor-sidecar` answers `GET /health` and `POST /extract` with real structured output via OpenRouter and `@lightfeed/extractor`, without Redis.*

### Task 1.1: Scaffold Node service and container - 📋 Planned

*Spec Reference: Technical Approach § Implementation Strategy (item 1); Technical Constraints (stack, OpenRouter); Affected Components*

- [ ] 1.1.1 **Create `extractor-sidecar/` with package manifest and lockfile** - 📋 Planned
  - *Hint*: Pin `@lightfeed/extractor`, `@langchain/openai`, `zod`; use **TypeScript**, **Express**, **`npm`** + **`package-lock.json`**, Node LTS per **Implementation decisions** table.
  - *Consider*: OpenRouter env vars (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, optional `HTTP-Referer` / `X-Title`); sidecar-only secrets per spec.
  - *Files*: `extractor-sidecar/package.json`, `extractor-sidecar/package-lock.json`, `extractor-sidecar/Dockerfile`, `extractor-sidecar/.env.example`, `.dockerignore`
  - *Risk*: Version drift between LangChain and extractor—lock versions and verify against extractor README.
  - **IMPLEMENTATION PLAN**:
    - **Scaffold**:
      - Add entrypoint `src/index.ts` (or `src/server.ts`) that reads configuration from named environment constants (no magic strings in call sites).
      - Add `extractor-sidecar/.env.example` listing sidecar variables (OpenRouter, `EXTRACT_MAX_LENGTH`, optional `REDIS_URL`, etc.) so local and Compose stay aligned.
      - Dockerfile: multi-stage build; expose port **3000**; non-root user when practical.
    - **Configuration**:
      - Centralize defaults per **Implementation decisions**: `EXTRACT_MAX_LENGTH` `512000`, OpenRouter base URL `https://openrouter.ai/api/v1`, `EXTRACT_OPENROUTER_TIMEOUT_MS` **115000**, `EXTRACT_MAX_JSON_BODY_BYTES` **2097152**.
    - **Testing Strategy**:
      - **Code Quality**: `npm run lint` / `tsc --noEmit`; formatter as project standard.
      - **Manual**: `curl` to `/health` locally and in container.

### Task 1.2: Implement `GET /health` - 📋 Planned

*Spec Reference: Functional Requirements (Sidecar `GET /health`); Acceptance Criteria*

- [ ] 1.2.1 **Liveness endpoint for Compose healthchecks** - 📋 Planned
  - *Hint*: Match patterns used by `searxng-mcp` health (`mcp-server/server.py` `health_endpoint`).
  - *Consider*: Return 200 only when process is ready (e.g. after env validation); avoid leaking secrets in body.
  - *Files*: sidecar server module
  - *Risk*: Over-strict health if OpenRouter is checked synchronously—prefer “process up” unless spec requires upstream check (spec says liveness).
  - **IMPLEMENTATION PLAN**:
    - **Health**:
      - `GET /health` → JSON `{ "status": "ok" }` or similar with HTTP 200.
    - **Testing Strategy**:
      - **Integration**: HTTP GET returns 200 in test harness or container.

### Task 1.3: JSON Schema subset validation and Zod builder - 📋 Planned

*Spec Reference: JSON Schema subset (v1) and Zod mapping; Technical Approach § Investigation Requirements*

- [ ] 1.3.1 **Validate supported subset and reject unsupported keywords with HTTP 400** - 📋 Planned
  - *Hint*: Spec requires explicit rejection of `$ref`, combinators, etc.; nullable only via **`type: ["T", "null"]`** per **Implementation decisions** (reject **`nullable: true`** in v1).
  - *Consider*: **Hand-rolled** recursive builder only—see **Implementation decisions** (no unconstrained third-party JSON Schema→Zod for full Draft).
  - *Files*: `extractor-sidecar` module(s) for schema parsing, e.g. `schema-to-zod.ts`
  - *Risk*: Subtle mismatch with LLM output—pair with extractor/Zod validation and clear 400 paths before LLM when conversion fails.
  - **IMPLEMENTATION PLAN**:
    - **Subset**:
      - Walk JSON Schema object; reject unknown/unsupported keys with stable error messages (spec: sidecar 400, no partial LLM call on conversion failure).
    - **`additionalProperties` (spec § JSON Schema subset)**:
      - Follow **Implementation decisions**: reject **`additionalProperties: true`**; if omitted, treat as **`false`**; Zod objects use **`.strict()`**.
    - **Zod**:
      - Map `description` to `.describe()`; arrays and nested objects per spec.
    - **Testing Strategy**:
      - **Unit Testing**: Valid minimal schemas; unsupported `$ref` / `allOf`; nested object + array of objects per Investigation Requirements.

### Task 1.4: `POST /extract` — OpenRouter + `extract()` - 📋 Planned

*Spec Reference: Functional Requirements (Sidecar `POST /extract`); Problem Statement; Client workflow*

- [ ] 1.4.1 **Wire LangChain `ChatOpenAI` to OpenRouter and call `extract()`** - 📋 Planned
  - *Hint*: `@lightfeed/extractor` README for `ContentFormat`, `extract()`, optional `maxInputTokens`.
  - *Consider*: Enforce `EXTRACT_MAX_LENGTH` on `content` before LLM (**reject** if over limit); reject empty/whitespace-only body; raw body cap **`EXTRACT_MAX_JSON_BODY_BYTES`** default **2097152**.
  - *Files*: sidecar route handler, LLM factory module
  - *Risk*: Invalid JSON from model—document reliance on extractor mitigations; map sidecar errors to structured responses.
  - **IMPLEMENTATION PLAN**:
    - **Request body**:
      - Accept `content`, `source_url`, `json_schema`, optional `prompt`, `content_format` (`markdown` | `txt` | `html`, default `txt`), optional `extraction_context`, optional `maxInputTokens`.
    - **`content_format` → extractor `ContentFormat`**:
      - Document in README a fixed mapping: `txt` → plain text format, `markdown` → markdown, `html` → HTML—each maps to the corresponding **`ContentFormat`** enum/value from `@lightfeed/extractor` (verify names against installed package version during Task 1.4).
    - **`extraction_context` → extractor**:
      - Pass through to the extractor’s `extractionContext` (or documented equivalent) when present; omit when absent.
    - **OpenRouter attribution headers**:
      - Wire optional env-driven `HTTP-Referer` and `X-Title` on the LangChain client when supported (spec § OpenRouter).
    - **Flow**:
      - Enforce **`EXTRACT_MAX_JSON_BODY_BYTES`** before parsing (**413** if over) → parse JSON → validate payload → enforce **`EXTRACT_MAX_LENGTH`** on `content` (**413** if over) → reject empty/whitespace-only (**400**) → convert schema to Zod → `extract({ llm, content, format, schema, extractionContext?, ... })` → return JSON shape including `data`, `usage`, optional `processedContent`, `cached: false` until Phase 2.
    - **Errors**:
      - Map OpenRouter 4xx/5xx to structured error responses; never echo API keys.
      - Body over **`EXTRACT_MAX_JSON_BODY_BYTES`** or **`content`** over **`EXTRACT_MAX_LENGTH`**: **413**; malformed JSON, bad schema, conversion failure, empty content: **400** (per **Implementation decisions**).
    - **Testing Strategy**:
      - **Integration**: Mock OpenRouter HTTP layer or use test key in isolated env; verify structured `data` for a minimal schema.
      - **Test Cases**: Oversized `content`; empty content; unsupported schema; oversize JSON body returns documented status.

### Phase 1 Validation - 📋 Planned

- **Acceptance Criteria**: Sidecar `/health` 200; `/extract` returns structured JSON for valid subset schema; unsupported schema returns **400** with reason; limits enforced before LLM; oversize body or **`content`** returns **413**; other client errors **400** per **Implementation decisions**.
- **Testing Strategy**: Manual `curl` + unit tests for schema module; optional integration with mocked fetch to OpenRouter.
- **Rollback Plan**: Remove sidecar service from future Compose until Phase 4; MCP unchanged until Phase 3.

---

## Phase 2: Redis-backed LLM result cache (sidecar) - 📋 Planned

*Incremental Goal: Identical extraction inputs hit Redis and skip OpenRouter; outage degrades to uncached LLM path.*

### Task 2.1: Redis client and connection policy - 📋 Planned

*Spec Reference: Caching (LLM result cache); Edge Cases*

- [ ] 2.1.1 **Connect via `REDIS_URL` with dedicated DB index and key prefix** - 📋 Planned
  - *Hint*: Spec recommends logical DB (e.g. `/1`) and prefix `extract:`; `docker-compose.yml` already defines `redis` on `searxng`.
  - *Consider*: Connection pooling and timeouts for low concurrency; log warnings, do not fail request if Redis down when cache enabled.
  - *Files*: sidecar Redis module, env parsing for `EXTRACT_CACHE_ENABLED`, `EXTRACT_CACHE_TTL_SECONDS` (default `86400`)
  - *Risk*: Misconfigured URL—lazy connect defers failure to first cache op; log clearly.
  - **IMPLEMENTATION PLAN**:
    - **Connection policy**:
      - **Lazy connect** on first cache operation only (**Implementation decisions**); non-fatal errors when Redis unavailable; tests must assert this behavior.
    - **Env**:
      - **`EXTRACT_CACHE_ENABLED`**: **`true`** if `REDIS_URL` set, else **`false`**; document in README.
    - **Client**:
      - **`ioredis`**; prefix all keys **`extract:`**; **`REDIS_URL`** in Compose **`redis://redis:6379/1`**.
    - **Testing Strategy**:
      - **Integration**: Redis up → cache works; Redis stopped → requests still succeed with warning logs (per Edge Cases table).

### Task 2.2: Deterministic cache key and serialization - 📋 Planned

*Spec Reference: Caching — Cache key; Value; TTL*

- [ ] 2.2.1 **Implement stable hash over model, canonical schema, prompt, format, context, content hash** - 📋 Planned
  - *Hint*: Canonical JSON: sorted keys; same normalization for `content` as used before hashing (post–`EXTRACT_MAX_LENGTH` truncation).
  - *Consider*: Include `OPENROUTER_MODEL` in key; SHA-256 hex of normalized content string.
  - *Files*: sidecar cache module
  - *Risk*: Key instability if serialization differs between runs—unit test golden vectors for cache key inputs.
  - **IMPLEMENTATION PLAN**:
    - **Per-request order (spec: cache lookup before LLM)**:
      1. Normalize/truncate `content` per `EXTRACT_MAX_LENGTH` (same normalization as used in cache key input).
      2. If cache enabled: **lookup** by deterministic key → on **hit**, return stored payload with `cached: true` (skip schema validation and OpenRouter).
      3. On **miss**: validate JSON Schema subset → convert to Zod → call OpenRouter → on success **store** in Redis with TTL → return with `cached: false`.
    - **Key**:
      - Concatenate or tuple-hash documented fields; use SHA-256 for content component. (`source_url` is not part of the key per spec—the content hash captures page changes.)
    - **Value**:
      - Store payload needed to reconstruct client-visible response; TTL from `EXTRACT_CACHE_TTL_SECONDS`.
    - **Response**:
      - Set **`cached: true`** on hits; **omit `usage`** on hits (**Implementation decisions**).
    - **Testing Strategy**:
      - **Unit Testing**: Two requests with identical inputs → second is cache hit; change content byte → miss; change schema → miss.

### Phase 2 Validation - 📋 Planned

- **Acceptance Criteria**: Second identical `POST /extract` returns `cached: true` without duplicate OpenRouter invocation (verify via mock or logs); Redis failure still returns 200 with LLM result.
- **Testing Strategy**: Integration test with Redis container or Testcontainers; mock LLM to count invocations.
- **Rollback Plan**: Feature-flag cache via `EXTRACT_CACHE_ENABLED=false` without removing code paths.

---

## Phase 3: MCP (Python) — `EXTRACT_ENABLED`, fetch, sidecar proxy - 📋 Planned

*Incremental Goal: When enabled, MCP tool `extract` performs internal fetch then POSTs to sidecar; when disabled, tool hidden and calls rejected clearly.*

### Task 3.1: Configuration and truthy parsing - 📋 Planned

*Spec Reference: Technical Constraints (env table); Functional Requirements (`EXTRACT_ENABLED`)*

- [ ] 3.1.1 **Add env constants and parsers for extract-related variables** - 📋 Planned
  - *Hint*: Reuse a single helper for truthy/falsy (`1`, `true`, `yes` / `0`, `false`, `no`, unset).
  - *Consider*: Defaults: `EXTRACT_ENABLED=false`, `EXTRACT_TIMEOUT=120`, `EXTRACT_MAX_LENGTH=512000`, `EXTRACTOR_SIDECAR_URL` required when enabled (fail at tool call with clear message if missing).
  - *Files*: `mcp-server/server.py` (keep extract config and helpers in this file unless a separate module materially reduces size)
  - *Risk*: Accidentally using `DEFAULT_TIMEOUT` (5s) for sidecar—spec forbids; use `EXTRACT_TIMEOUT` only.
  - **IMPLEMENTATION PLAN**:
    - **Constants**:
      - Named constants for defaults and error messages (no magic strings).
    - **Testing Strategy**:
      - **Unit Testing**: Parser covers accepted truthy/falsy variants; default values when unset.
    - **Document (README)**:
      - Origin **fetch** still uses `SearXNGClient` / `DEFAULT_TIMEOUT` (5s) for the target URL—only the **MCP→sidecar** hop uses `EXTRACT_TIMEOUT`. Slow or hanging origins may fail before sidecar is contacted; not a violation of the spec (spec isolates LLM/sidecar timeouts).

### Task 3.2: Conditional tool registration and `handle_extract_tool` - 📋 Planned

*Spec Reference: Functional Requirements (MCP tool `extract`); Behavior steps 1–5*

- [ ] 3.2.1 **Use `build_tool_definitions()` for `list_tools` and `tools_endpoint`; include `extract` only when enabled** - 📋 Planned
  - *Hint*: Current `list_tools` returns a fixed list (`mcp-server/server.py` ~277–325); mirror pattern for `tools_endpoint` JSON (~577–624) so HTTP clients see the same tool set.
  - *Consider*: `call_tool`: when disabled, reject `extract` with clear message; when enabled, unknown tool still uses `ERROR_UNKNOWN_TOOL`.
  - *Files*: `mcp-server/server.py`
  - *Risk*: Drift between MCP `list_tools` and `tools_endpoint`—extract helper to build tool definitions once.
  - **IMPLEMENTATION PLAN**:
    - **`extract` tool `inputSchema` (must match spec § Client inputs)**:
      - Required: `url`, `json_schema`.
      - Optional: `prompt`, `content_format`, `extraction_context`, `headers`, `max_content_length` (fetch-step cap, same semantics as `fetch` tool).
    - **Fetch**:
      - Reuse `SearXNGClient.fetch` (`server.py` `SearXNGClient.fetch`) for the URL; same `headers` support as `handle_fetch_tool`.
    - **After fetch (order matters—spec: fetch semantics then `EXTRACT_MAX_LENGTH`)**:
      - If `error` in result, return fetch error—do not call sidecar.
      - Apply optional **`max_content_length`** to the fetched string first (same caps as `handle_fetch_tool` / `MAX_FETCH_CONTENT_LIMIT`), then enforce **`EXTRACT_MAX_LENGTH`** by **rejecting** with clear error text (stdio) or **413** on HTTP if over limit (**Implementation decisions**).
      - Reject empty/whitespace-only content with clear error (**400**-class message).
    - **Sidecar**:
      - `POST` JSON to `{EXTRACTOR_SIDECAR_URL}/extract` using **`aiohttp` async client** (or equivalent non-blocking I/O)—do **not** use blocking `urllib` inside async handlers (avoids stalling the event loop).
    - **Timeout**:
      - Use `EXTRACT_TIMEOUT` (seconds) for entire sidecar request.
    - **Response**:
      - Return `TextContent` with JSON string or stable serialization including sidecar `cached` when present.
    - **Errors (spec Edge Cases)**:
      - Sidecar unreachable / connection errors: clear **`TextContent`** to MCP client; HTTP mirror returns **502** + stable JSON (**Implementation decisions**).
      - Sidecar/OpenRouter errors: forward structured message without leaking secrets.
    - **Testing Strategy**:
      - **Unit/Mock**: Mock `aiohttp` responses for sidecar; verify fetch failure skips sidecar; verify timeout uses `EXTRACT_TIMEOUT`; verify `max_content_length` applied before `EXTRACT_MAX_LENGTH`.

### Task 3.3: `POST /extract` HTTP route (mirror) with same gating - 📋 Planned

*Spec Reference: HTTP mirror; `EXTRACT_ENABLED` for HTTP*

- [ ] 3.3.1 **Add `/extract` route and stable JSON when disabled** - 📋 Planned
  - *Hint*: Parallel `fetch_endpoint` structure (`server.py` ~527–551).
  - *Consider*: Same JSON body shape as MCP tool input; map sidecar/MCP errors to documented status codes (502/503 sidecar unreachable per spec).
  - *Files*: `mcp-server/server.py`, `create_web_app` router registration (~627–634)
  - *Risk*: Duplicating handler logic—delegate to shared async function used by both `call_tool` and HTTP.
  - **IMPLEMENTATION PLAN**:
    - **Route**:
      - When `EXTRACT_ENABLED` is **false**: return **404** with stable JSON body (e.g. `{ "error": "extract disabled", "code": "..." }`)—**404** is preferred so “feature not available” is distinct from **503** (service unavailable / sidecar down).
    - **Enabled path**:
      - **413** vs **400** per **Implementation decisions** table; sidecar down → **502**; document exact JSON keys in `API_DOCUMENTATION.md`.
    - **Testing Strategy**:
      - **Integration**: `curl` POST with enabled/disabled flag; assert **404** body when disabled; assert **502** when sidecar mocked unreachable.

### Phase 3 Validation - 📋 Planned

- **Acceptance Criteria**: `EXTRACT_ENABLED` off → `extract` absent from `list_tools` and `/tools`, HTTP `POST /extract` returns **404** + stable JSON; on → tool present and end-to-end works with running sidecar; secrets not in MCP responses; sidecar down returns **502** on HTTP mirror.
- **Testing Strategy**: Manual MCP + HTTP; automated tests with mocks.
- **Rollback Plan**: Set `EXTRACT_ENABLED=false` in Compose.

---

## Phase 4: Docker Compose, env examples, and documentation - 📋 Planned

*Incremental Goal: One-command stack includes sidecar and wired Redis; operators can configure from README.*

### Task 4.1: `docker-compose.yml` updates - 📋 Planned

*Spec Reference: Success criteria; Technical Constraints; Caching — Redis*

- [ ] 4.1.1 **Add `extractor-sidecar` service on `searxng` with healthcheck and dependencies** - 📋 Planned
  - *Hint*: Only **`extractor-sidecar`** should `depends_on` **redis** (or rely on network-only ordering)—**`searxng-mcp` does not use Redis**; do not add Redis as an MCP dependency.
  - *Consider*: **No** `depends_on: extractor-sidecar` on MCP (**Implementation decisions**); document that MCP may return **502** until sidecar is up.
  - *Consider*: `EXTRACTOR_SIDECAR_URL=http://extractor-sidecar:3000`; sidecar `REDIS_URL=redis://redis:6379/1`.
  - *Files*: `docker-compose.yml`; repository root `.env.example` **create or update** (if missing) documenting `EXTRACT_ENABLED`, `EXTRACTOR_SIDECAR_URL`, sidecar OpenRouter vars by reference—keep one source of truth with README.
  - *Risk*: Redis memory—spec lists recommendations (maxmemory, volatile-lru, optional mem_limit); implement only what is safe for shared redis-data volume (see spec warning about persistence).
  - **IMPLEMENTATION PLAN**:
    - **Service**:
      - Build context `./extractor-sidecar`; wire env consistently with `extractor-sidecar/.env.example` and root `.env.example`.
    - **MCP env**:
      - Full-stack example sets **`EXTRACT_ENABLED=true`**; document **`EXTRACT_ENABLED=false`** for minimal stacks.
    - **Testing Strategy**:
      - **Manual**: `docker compose up`, hit MCP `/health`, sidecar `/health`, then `extract` flow.

### Task 4.2: Documentation - 📋 Planned

*Spec Reference: Affected Components; Privacy; Redis tuning*

- [ ] 4.2.1 **Update README files and API documentation** - 📋 Planned
  - *Hint*: `mcp-server/README.md`, root `README.md`, `API_DOCUMENTATION.md` per spec.
  - *Consider*: Document `EXTRACT_MAX_LENGTH` vs `MAX_FETCH_CONTENT_LIMIT` (1 MiB); privacy note for cache and LLM; OpenRouter-only-on-sidecar.
  - *Files*: `README.md`, `mcp-server/README.md`, `API_DOCUMENTATION.md`
  - *Risk*: Stale port numbers—keep in sync with `PORT` / Compose.
  - **IMPLEMENTATION PLAN**:
    - **Content**:
      - Tool contract, env tables, example `curl` for `POST /extract`, troubleshooting (502 when sidecar down).
    - **Testing Strategy**:
      - **Review**: Copy-paste examples against running stack.

### Phase 4 Validation - 📋 Planned

- **Acceptance Criteria**: New developer can enable extract from documented env vars; API doc matches request/response.
- **Testing Strategy**: Follow README from clean clone.
- **Rollback Plan**: Omit sidecar service from Compose profile or document profile name for minimal stack.

---

## Phase 5: Automated tests and quality gates - 📋 Planned

*Incremental Goal: Regressions caught in CI; cache keys and schema conversion locked by tests.*

### Task 5.1: Test infrastructure - 📋 Planned

*Spec Reference: Implementation Tasks (Tests); Investigation Requirements*

- [ ] 5.1.1 **Add pytest (MCP) and Vitest (sidecar)** - 📋 Planned
  - *Hint*: Repository currently has no `test_*.py` files—introduce minimal `pytest` layout under `mcp-server/tests/`; sidecar `npm test`.
  - *Consider*: CI workflow if `.github/workflows` exists—add test job.
  - *Files*: `pytest.ini` (or `pyproject.toml` if repo standardizes), `mcp-server/requirements-dev.txt` for dev deps
  - *Risk*: Docker-in-CI for Redis—use mocks or ephemeral Redis service in CI matrix.
  - **IMPLEMENTATION PLAN**:
    - **MCP**:
      - Mock **`aiohttp`** (primary client for sidecar POST); test `list_tools` conditional inclusion and shared tool-definition helper.
    - **Sidecar**:
      - Unit: schema→Zod; cache key vectors; integration: mock OpenRouter, second request hits cache.

### Task 5.2: Acceptance-oriented tests - 📋 Planned

*Spec Reference: Acceptance Criteria (full list)*

- [ ] 5.2.1 **Map each acceptance criterion to at least one test or documented manual check** - 📋 Planned
  - *Consider*: `EXTRACT_TIMEOUT` / `EXTRACT_MAX_LENGTH` behavior when unset (defaults).
  - **IMPLEMENTATION PLAN**:
    - **Traceability matrix** (fill in test name or “manual” when executing):
      - `extract` in `list_tools` with correct `inputSchema` → *test / manual:* …
      - Structured `data` for valid schema (integration / real key) → …
      - Second identical request → `cached: true`, no duplicate OpenRouter charge → …
      - Sidecar `GET /health` 200; Compose healthcheck → …
      - Unsupported `json_schema` → 400, message via MCP → …
      - Sidecar/OpenRouter failure without secret leakage → …
      - `EXTRACT_ENABLED` off → tool absent; on → works → …
      - `EXTRACT_TIMEOUT` / `EXTRACT_MAX_LENGTH` defaults when env unset → …
      - Payload limits enforced; relationship to fetch 1 MiB cap documented → …
    - **Coverage**:
      - Tool not advertised when disabled; 400 on unsupported schema surfaced through MCP; no secret leakage in error paths; HTTP **404** when extract disabled; **502** when sidecar unreachable per **Implementation decisions**.
    - **Testing Strategy**:
      - **Coverage**: Critical paths per spec table Edge Cases (including Redis degrade, empty content, oversize payload).

### Phase 5 Validation - 📋 Planned

- **Acceptance Criteria**: CI green; critical unit/integration tests pass locally.
- **Testing Strategy**: Run pytest and npm test in Docker or host as documented.
- **Rollback Plan**: Mark tests as optional in CI temporarily if flaky—prefer fixing flakiness.

---

## Critical Considerations - 📋 Planned

- **Performance**: LLM latency dominates; cache reduces repeat cost; `EXTRACT_TIMEOUT` should exceed typical OpenRouter latency but bound hung requests.
- **Origin fetch vs sidecar timeout**: Page fetch uses the existing client timeout (`DEFAULT_TIMEOUT` / SearXNG fetch behavior)—do not confuse with `EXTRACT_TIMEOUT`, which applies only to the MCP→sidecar HTTP call.
- **Security**: OpenRouter key only in sidecar env; MCP must not log full page content at DEBUG without awareness; Redis may hold PII—document.
- **Scalability**: Single-user profile per spec; Redis `maxmemory` and eviction policy under load; optional Compose `mem_limit` on `redis`.
- **Monitoring**: Log cache hit/miss and evictions in ops notes; sidecar logs OpenRouter errors without secrets.
- **Cross-Phase Dependencies**: Phase 2 requires Phase 1 routes; Phase 3 requires Phase 1 sidecar API; Phase 4 assumes Phase 1–3 artifacts; Phase 5 validates all.

---

## Research & Validation Completed

- **Dependencies Verified**: `mcp-server` uses `aiohttp` for the inbound web server (`server.py`); outbound MCP→sidecar `POST` should use **`aiohttp` (async)** as well—there is no existing outbound pattern in `server.py` today (fetch uses sync `urllib`). `SearXNGClient.fetch` exists and returns `content`, `error`, etc.; `docker-compose.yml` defines `redis` and `searxng` networks.
- **Patterns Identified**: HTTP endpoints mirror tool behavior (`fetch_endpoint` vs `handle_fetch_tool`); tools duplicated in `tools_endpoint`—`extract` must follow same pattern with gating.
- **Assumptions Validated**: No existing Python test suite—tests are net-new; `list_tools` is synchronous structure—dynamic tool list requires refactor to shared builder.

---

## Critical Sanity Check (summary)

| Check | Result |
|-------|--------|
| Incremental phases testable | Yes: sidecar alone → +Redis → +MCP → +Compose → +tests |
| Spec coverage | Functional, caching, edge cases, acceptance criteria mapped to phases |
| `tools_endpoint` / `list_tools` parity | Task 3.2 explicitly requires both + shared `inputSchema` fields |
| Separate timeouts | Phase 1 (`EXTRACT_OPENROUTER_TIMEOUT_MS`) vs Phase 3 (`EXTRACT_TIMEOUT`) vs origin fetch (`DEFAULT_TIMEOUT` on `SearXNGClient.fetch`)—do not reuse 5s for sidecar hop |
| Fetch path reuse | Task 3.2 uses `SearXNGClient.fetch` |
| Fetch length order | `max_content_length` (fetch step) then `EXTRACT_MAX_LENGTH` (Task 3.2) |
| MCP→sidecar HTTP | Async client (`aiohttp`); avoid blocking `urllib` in async handlers |
| Disabled extract HTTP | **404** + stable JSON when `EXTRACT_ENABLED` false (Task 3.3) |
| Redis connect policy | **Lazy** first cache op; **`ioredis`**; DB **`/1`** |
| HTTP status codes | **413** limit; **400** client/schema; **404** disabled; **502** sidecar down |
| Nullable / objects | **`type: ["T","null"]`**; **strict** objects; **`additionalProperties`** per **Implementation decisions** |

*If product requirements change, update **Implementation decisions** first, then tasks and `docs/extract-sidecar-specification.md` as needed.*
