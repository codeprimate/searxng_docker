import express, { type Request, type Response } from "express";

import type { AppConfig } from "./config.js";
import {
  type ExtractRequestBody,
  runExtract,
} from "./extract-runner.js";

export function parseExtractBody(raw: Record<string, unknown>): ExtractRequestBody {
  const maxRaw =
    raw.maxInputTokens ?? raw.max_input_tokens;
  let maxInputTokens: number | undefined;
  if (typeof maxRaw === "number" && Number.isFinite(maxRaw)) {
    maxInputTokens = maxRaw;
  }

  let extraction_context: Record<string, unknown> | undefined;
  const ec = raw.extraction_context;
  if (ec !== undefined && ec !== null && typeof ec === "object" && !Array.isArray(ec)) {
    extraction_context = ec as Record<string, unknown>;
  }

  let validation_mode: string | undefined;
  const vm = raw.validation_mode;
  if (typeof vm === "string") {
    validation_mode = vm;
  }

  return {
    content: typeof raw.content === "string" ? raw.content : "",
    source_url: typeof raw.source_url === "string" ? raw.source_url : "",
    json_schema: raw.json_schema,
    prompt: typeof raw.prompt === "string" ? raw.prompt : undefined,
    content_format:
      typeof raw.content_format === "string" ? raw.content_format : undefined,
    extraction_context,
    maxInputTokens,
    validation_mode,
  };
}

export function createApp(config: AppConfig): express.Express {
  const app = express();
  app.disable("x-powered-by");
  app.use(
    express.json({
      limit: config.extractMaxJsonBodyBytes,
    }),
  );

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/extract", async (req: Request, res: Response) => {
    const raw = req.body as Record<string, unknown> | null;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      res.status(400).json({ error: "JSON body must be an object" });
      return;
    }
    const body = parseExtractBody(raw);
    const result = await runExtract(body, config);
    if ("error" in result && "status" in result) {
      res.status(result.status).json({ error: result.error });
      return;
    }
    res.status(200).json(result);
  });

  app.use(
    (
      err: unknown,
      _req: Request,
      res: Response,
      next: (e?: unknown) => void,
    ) => {
      if (err instanceof SyntaxError) {
        res.status(400).json({ error: "Invalid JSON body" });
        return;
      }
      const e = err as { status?: number; type?: string };
      if (e.status === 413 || e.type === "entity.too.large") {
        res.status(413).json({
          error: `request body exceeds EXTRACT_MAX_JSON_BODY_BYTES (${config.extractMaxJsonBodyBytes})`,
        });
        return;
      }
      next(err);
    },
  );

  return app;
}
