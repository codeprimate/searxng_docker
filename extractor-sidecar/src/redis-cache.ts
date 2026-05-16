import { Redis } from "ioredis";

import type { AppConfig } from "./config.js";
import { REDIS_KEY_PREFIX } from "./config.js";

export interface CachedExtractPayload {
  data: unknown;
}

let redisSingleton: Redis | null = null;

export function getRedisClient(config: AppConfig): Redis | null {
  if (!config.cacheEnabled || !config.redisUrl) {
    return null;
  }
  if (!redisSingleton) {
    redisSingleton = new Redis(config.redisUrl, {
      lazyConnect: true,
      maxRetriesPerRequest: 1,
      enableReadyCheck: false,
    });
    redisSingleton.on("error", (err: Error) => {
      console.warn("[extractor-sidecar] Redis client error (cache degraded):", err.message);
    });
  }
  return redisSingleton;
}

export function redisKeyForHash(keyHash: string): string {
  return `${REDIS_KEY_PREFIX}${keyHash}`;
}

export async function cacheGet(
  client: Redis | null,
  keyHash: string,
): Promise<CachedExtractPayload | null> {
  if (!client) {
    return null;
  }
  try {
    const raw = await client.get(redisKeyForHash(keyHash));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CachedExtractPayload;
    if (parsed && typeof parsed === "object" && "data" in parsed) {
      return parsed;
    }
    return null;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.warn("[extractor-sidecar] Redis get failed (cache miss):", msg);
    return null;
  }
}

export async function cacheSet(
  client: Redis | null,
  keyHash: string,
  payload: CachedExtractPayload,
  ttlSeconds: number,
): Promise<void> {
  if (!client) {
    return;
  }
  try {
    await client.set(
      redisKeyForHash(keyHash),
      JSON.stringify(payload),
      "EX",
      ttlSeconds,
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.warn("[extractor-sidecar] Redis set failed (continuing without cache):", msg);
  }
}
