import { ChatOpenAI } from "@langchain/openai";

import type { AppConfig } from "./config.js";

export function createOpenRouterLlm(config: AppConfig): ChatOpenAI {
  const headers: Record<string, string> = {};
  if (config.openRouterHttpReferer) {
    headers["HTTP-Referer"] = config.openRouterHttpReferer;
  }
  if (config.openRouterXTitle) {
    headers["X-Title"] = config.openRouterXTitle;
  }
  return new ChatOpenAI({
    model: config.openRouterModel,
    temperature: 0,
    apiKey: config.openRouterApiKey,
    timeout: config.extractOpenRouterTimeoutMs,
    configuration: {
      baseURL: config.openRouterBaseUrl,
      defaultHeaders: Object.keys(headers).length > 0 ? headers : undefined,
    },
  });
}
