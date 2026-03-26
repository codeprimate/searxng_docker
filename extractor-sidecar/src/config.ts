/**
 * Environment-backed configuration (named constants; defaults in one place).
 */
import process from "node:process";

export const ENV_OPENROUTER_API_KEY = "OPENROUTER_API_KEY";
export const ENV_OPENROUTER_MODEL = "OPENROUTER_MODEL";
export const ENV_OPENROUTER_BASE_URL = "OPENROUTER_BASE_URL";
export const ENV_OPENROUTER_HTTP_REFERER = "OPENROUTER_HTTP_REFERER";
export const ENV_OPENROUTER_X_TITLE = "OPENROUTER_X_TITLE";
export const ENV_EXTRACT_MAX_LENGTH = "EXTRACT_MAX_LENGTH";
export const ENV_EXTRACT_MAX_JSON_BODY_BYTES = "EXTRACT_MAX_JSON_BODY_BYTES";
export const ENV_EXTRACT_OPENROUTER_TIMEOUT_MS = "EXTRACT_OPENROUTER_TIMEOUT_MS";
export const ENV_PORT = "PORT";
export const ENV_REDIS_URL = "REDIS_URL";
export const ENV_EXTRACT_CACHE_ENABLED = "EXTRACT_CACHE_ENABLED";
export const ENV_EXTRACT_CACHE_TTL_SECONDS = "EXTRACT_CACHE_TTL_SECONDS";

export const DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
/** Unicode code units cap for `content`; 512 KiB */
const KIBIBYTE = 1024;
export const DEFAULT_EXTRACT_MAX_LENGTH = 512 * KIBIBYTE;
/** Raw POST body cap (JSON payload); 512 KiB */
export const DEFAULT_EXTRACT_MAX_JSON_BODY_BYTES = 512 * KIBIBYTE;
export const DEFAULT_EXTRACT_OPENROUTER_TIMEOUT_MS = 115000;
export const DEFAULT_LISTEN_PORT = 3000;
export const DEFAULT_EXTRACT_CACHE_TTL_SECONDS = 86400;

export const REDIS_KEY_PREFIX = "extract:";

export function parsePositiveInt(
  raw: string | undefined,
  defaultValue: number,
  envName: string,
): number {
  if (raw === undefined || raw === "") {
    return defaultValue;
  }
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 0) {
    throw new Error(`${envName} must be a non-negative integer`);
  }
  return n;
}

export function parseCacheEnabled(
  redisUrl: string | undefined,
  rawFlag: string | undefined,
): boolean {
  if (!redisUrl || redisUrl === "") {
    return false;
  }
  if (rawFlag === undefined || rawFlag === "") {
    return true;
  }
  return parseTruthy(rawFlag);
}

/** Same truthy/falsy convention as MCP: 1/true/yes vs 0/false/no. */
export function parseTruthy(raw: string): boolean {
  const normalized = raw.trim().toLowerCase();
  if (["1", "true", "yes"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no"].includes(normalized)) {
    return false;
  }
  throw new Error(`Invalid boolean env value: ${raw}`);
}

export interface AppConfig {
  openRouterApiKey: string | undefined;
  openRouterModel: string;
  openRouterBaseUrl: string;
  openRouterHttpReferer: string | undefined;
  openRouterXTitle: string | undefined;
  extractMaxLength: number;
  extractMaxJsonBodyBytes: number;
  extractOpenRouterTimeoutMs: number;
  listenPort: number;
  redisUrl: string | undefined;
  cacheEnabled: boolean;
  cacheTtlSeconds: number;
}

export function loadConfig(): AppConfig {
  const redisUrl = process.env[ENV_REDIS_URL]?.trim() || undefined;
  const cacheEnabled = parseCacheEnabled(
    redisUrl,
    process.env[ENV_EXTRACT_CACHE_ENABLED],
  );
  const cacheTtlSeconds = parsePositiveInt(
    process.env[ENV_EXTRACT_CACHE_TTL_SECONDS],
    DEFAULT_EXTRACT_CACHE_TTL_SECONDS,
    ENV_EXTRACT_CACHE_TTL_SECONDS,
  );

  return {
    openRouterApiKey: process.env[ENV_OPENROUTER_API_KEY]?.trim() || undefined,
    openRouterModel:
      process.env[ENV_OPENROUTER_MODEL]?.trim() || "openai/gpt-4o-mini",
    openRouterBaseUrl:
      process.env[ENV_OPENROUTER_BASE_URL]?.trim() || DEFAULT_OPENROUTER_BASE_URL,
    openRouterHttpReferer:
      process.env[ENV_OPENROUTER_HTTP_REFERER]?.trim() || undefined,
    openRouterXTitle: process.env[ENV_OPENROUTER_X_TITLE]?.trim() || undefined,
    extractMaxLength: parsePositiveInt(
      process.env[ENV_EXTRACT_MAX_LENGTH],
      DEFAULT_EXTRACT_MAX_LENGTH,
      ENV_EXTRACT_MAX_LENGTH,
    ),
    extractMaxJsonBodyBytes: parsePositiveInt(
      process.env[ENV_EXTRACT_MAX_JSON_BODY_BYTES],
      DEFAULT_EXTRACT_MAX_JSON_BODY_BYTES,
      ENV_EXTRACT_MAX_JSON_BODY_BYTES,
    ),
    extractOpenRouterTimeoutMs: parsePositiveInt(
      process.env[ENV_EXTRACT_OPENROUTER_TIMEOUT_MS],
      DEFAULT_EXTRACT_OPENROUTER_TIMEOUT_MS,
      ENV_EXTRACT_OPENROUTER_TIMEOUT_MS,
    ),
    listenPort: parsePositiveInt(
      process.env[ENV_PORT],
      DEFAULT_LISTEN_PORT,
      ENV_PORT,
    ),
    redisUrl,
    cacheEnabled,
    cacheTtlSeconds,
  };
}
