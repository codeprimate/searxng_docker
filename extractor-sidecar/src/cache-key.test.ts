import { describe, expect, it } from "vitest";

import { buildCacheKey, type CacheKeyParts } from "./cache-key.js";
import { VALIDATION_MODE_COERCE } from "./validation-mode.js";

describe("buildCacheKey", () => {
  it("is stable for identical inputs", () => {
    const a = buildCacheKey({
      model: "m1",
      validationMode: VALIDATION_MODE_COERCE,
      jsonSchema: { type: "object", properties: { x: { type: "string" } }, required: ["x"] },
      prompt: "",
      contentFormat: "txt",
      extractionContext: undefined,
      content: "hello",
    });
    const b = buildCacheKey({
      model: "m1",
      validationMode: VALIDATION_MODE_COERCE,
      jsonSchema: { type: "object", properties: { x: { type: "string" } }, required: ["x"] },
      prompt: "",
      contentFormat: "txt",
      extractionContext: undefined,
      content: "hello",
    });
    expect(a).toBe(b);
  });

  it("changes when content changes", () => {
    const base: Omit<CacheKeyParts, "content"> = {
      model: "m1",
      validationMode: VALIDATION_MODE_COERCE,
      jsonSchema: { type: "object", properties: { x: { type: "string" } }, required: ["x"] },
      prompt: "",
      contentFormat: "txt",
      extractionContext: undefined,
    };
    const a = buildCacheKey({ ...base, content: "a" });
    const b = buildCacheKey({ ...base, content: "b" });
    expect(a).not.toBe(b);
  });
});
