import { extract, ContentFormat } from "@lightfeed/extractor";

import { buildCacheKey } from "./cache-key.js";
import type { AppConfig } from "./config.js";
import { SchemaConversionError, jsonSchemaToZod } from "./schema-to-zod.js";
import { cacheGet, cacheSet, getRedisClient } from "./redis-cache.js";
import { createOpenRouterLlm } from "./llm.js";

export const ERR_EMPTY_CONTENT =
  "content must be non-empty and not whitespace-only";
export const ERR_MISSING_FIELDS =
  "content, source_url, and json_schema are required";
export const ERR_INVALID_CONTENT_FORMAT =
  'content_format must be one of: "txt", "markdown", "html"';
export const ERR_OPENROUTER_KEY =
  "OPENROUTER_API_KEY is not configured on the sidecar";

export interface ExtractRequestBody {
  content: string;
  source_url: string;
  json_schema: unknown;
  prompt?: string;
  content_format?: string;
  extraction_context?: Record<string, unknown>;
  maxInputTokens?: number;
}

export interface ExtractSuccessJson {
  data: unknown;
  processedContent: string;
  usage?: { inputTokens?: number; outputTokens?: number };
  cached: boolean;
}

export interface ExtractErrorResult {
  status: number;
  error: string;
}

function mapContentFormat(
  raw: string | undefined,
): ContentFormat {
  const f = (raw ?? "txt").toLowerCase();
  if (f === "txt") {
    return ContentFormat.TXT;
  }
  if (f === "markdown") {
    return ContentFormat.MARKDOWN;
  }
  if (f === "html") {
    return ContentFormat.HTML;
  }
  throw new Error(ERR_INVALID_CONTENT_FORMAT);
}

function isWhitespaceOnly(s: string): boolean {
  return s.trim().length === 0;
}

export async function runExtract(
  body: ExtractRequestBody,
  config: AppConfig,
): Promise<ExtractSuccessJson | ExtractErrorResult> {
  const content = body.content;
  const sourceUrl = body.source_url;
  const jsonSchema = body.json_schema;

  if (
    typeof content !== "string" ||
    typeof sourceUrl !== "string" ||
    jsonSchema === undefined
  ) {
    return { status: 400, error: ERR_MISSING_FIELDS };
  }

  if (isWhitespaceOnly(content)) {
    return { status: 400, error: ERR_EMPTY_CONTENT };
  }

  if (lenCodeUnits(content) > config.extractMaxLength) {
    return {
      status: 413,
      error: `content exceeds EXTRACT_MAX_LENGTH (${config.extractMaxLength} Unicode code units)`,
    };
  }

  let contentFormat: ContentFormat;
  try {
    contentFormat = mapContentFormat(body.content_format);
  } catch (e) {
    const msg = e instanceof Error ? e.message : ERR_INVALID_CONTENT_FORMAT;
    return { status: 400, error: msg };
  }

  if (!config.openRouterApiKey) {
    return { status: 503, error: ERR_OPENROUTER_KEY };
  }

  const prompt = typeof body.prompt === "string" ? body.prompt : "";
  const extractionContext = body.extraction_context;
  const maxInputTokens =
    typeof body.maxInputTokens === "number" && Number.isFinite(body.maxInputTokens)
      ? body.maxInputTokens
      : undefined;

  const formatStr = (body.content_format ?? "txt").toLowerCase();

  const keyHash = buildCacheKey({
    model: config.openRouterModel,
    jsonSchema,
    prompt,
    contentFormat: formatStr,
    extractionContext,
    content,
  });

  const redis = getRedisClient(config);
  const cached = await cacheGet(redis, keyHash);
  if (cached) {
    return {
      data: cached.data,
      processedContent: cached.processedContent,
      cached: true,
    };
  }

  let zodSchema;
  try {
    zodSchema = jsonSchemaToZod(jsonSchema);
  } catch (e) {
    const msg =
      e instanceof SchemaConversionError
        ? e.message
        : "JSON Schema conversion failed";
    return { status: 400, error: msg };
  }

  const llm = createOpenRouterLlm(config);

  try {
    const extractOpts = {
      llm: llm as never,
      content,
      format: contentFormat,
      schema: zodSchema,
      sourceUrl,
      ...(body.prompt !== undefined ? { prompt: body.prompt } : {}),
      ...(extractionContext !== undefined
        ? { extractionContext }
        : {}),
      ...(maxInputTokens !== undefined ? { maxInputTokens } : {}),
    };

    const result = await extract(extractOpts);

    const responseJson: ExtractSuccessJson = {
      data: result.data,
      processedContent: result.processedContent,
      usage: {
        inputTokens: result.usage.inputTokens,
        outputTokens: result.usage.outputTokens,
      },
      cached: false,
    };

    await cacheSet(
      redis,
      keyHash,
      { data: result.data, processedContent: result.processedContent },
      config.cacheTtlSeconds,
    );

    return responseJson;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    const safe = scrubErrorMessage(msg, config.openRouterApiKey);
    return { status: 502, error: `extraction failed: ${safe}` };
  }
}

function lenCodeUnits(s: string): number {
  return s.length;
}

function scrubErrorMessage(msg: string, apiKey: string | undefined): string {
  let out = msg;
  if (apiKey && apiKey.length > 4) {
    out = out.split(apiKey).join("[REDACTED]");
  }
  return out;
}
