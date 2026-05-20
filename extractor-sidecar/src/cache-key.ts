import { createHash } from "node:crypto";

import { canonicalJson } from "./canonical-json.js";
import type { ValidationMode } from "./validation-mode.js";

export const CACHE_KEY_VERSION = 2;

export interface CacheKeyParts {
  model: string;
  validationMode: ValidationMode;
  jsonSchema: unknown;
  prompt: string;
  contentFormat: string;
  extractionContext: Record<string, unknown> | undefined;
  content: string;
}

const FIELD_SEPARATOR = "\u0000";

/**
 * Deterministic Redis key hash from model, canonical schema, prompt, format, context, content hash.
 */
export function buildCacheKey(parts: CacheKeyParts): string {
  const schemaCanon = canonicalJson(parts.jsonSchema);
  const ctxCanon =
    parts.extractionContext === undefined
      ? ""
      : canonicalJson(parts.extractionContext);
  const contentHash = createHash("sha256")
    .update(parts.content, "utf8")
    .digest("hex");
  const keyMaterial = [
    String(CACHE_KEY_VERSION),
    parts.model,
    parts.validationMode,
    schemaCanon,
    parts.prompt,
    parts.contentFormat,
    ctxCanon,
    contentHash,
  ].join(FIELD_SEPARATOR);
  return createHash("sha256").update(keyMaterial, "utf8").digest("hex");
}
