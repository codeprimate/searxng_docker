import { describe, expect, it } from "vitest";

import { buildCacheKey } from "./cache-key.js";

describe("buildCacheKey", () => {
  it("is stable for identical inputs", () => {
    const a = buildCacheKey({
      model: "m1",
      jsonSchema: { type: "object", properties: { x: { type: "string" } }, required: ["x"] },
      prompt: "",
      contentFormat: "txt",
      extractionContext: undefined,
      content: "hello",
    });
    const b = buildCacheKey({
      model: "m1",
      jsonSchema: { type: "object", properties: { x: { type: "string" } }, required: ["x"] },
      prompt: "",
      contentFormat: "txt",
      extractionContext: undefined,
      content: "hello",
    });
    expect(a).toBe(b);
  });

  it("changes when content changes", () => {
    const base = {
      model: "m1",
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
