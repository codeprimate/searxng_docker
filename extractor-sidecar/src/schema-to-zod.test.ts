import { describe, expect, it } from "vitest";

import {
  SchemaConversionError,
  jsonSchemaToZod,
} from "./schema-to-zod.js";

describe("jsonSchemaToZod", () => {
  it("converts a minimal object schema", () => {
    const schema = {
      type: "object",
      properties: {
        title: { type: "string", description: "Title" },
      },
      required: ["title"],
    };
    const zod = jsonSchemaToZod(schema);
    const parsed = zod.parse({ title: "Hello" });
    expect(parsed).toEqual({ title: "Hello" });
  });

  it("rejects nullable keyword", () => {
    expect(() =>
      jsonSchemaToZod({
        type: "object",
        nullable: true,
        properties: { a: { type: "string" } },
        required: ["a"],
      }),
    ).toThrow(SchemaConversionError);
  });

  it("rejects additionalProperties true", () => {
    expect(() =>
      jsonSchemaToZod({
        type: "object",
        additionalProperties: true,
        properties: { a: { type: "string" } },
        required: ["a"],
      }),
    ).toThrow(SchemaConversionError);
  });

  it("supports nullable via type array", () => {
    const zod = jsonSchemaToZod({
      type: "object",
      properties: {
        title: { type: ["string", "null"] },
      },
      required: ["title"],
    });
    expect(zod.parse({ title: null })).toEqual({ title: null });
  });

  it("maps optional properties to null union (not Zod optional)", () => {
    const schema = {
      type: "object",
      properties: {
        title: { type: "string" },
        heading: { type: "string" },
      },
      required: ["title"],
    };
    const zod = jsonSchemaToZod(schema);
    expect(zod.parse({ title: "Hello", heading: "World" })).toEqual({
      title: "Hello",
      heading: "World",
    });
    expect(zod.parse({ title: "Hello", heading: null })).toEqual({
      title: "Hello",
      heading: null,
    });
    expect(() => zod.parse({ title: "Hello" })).toThrow();
  });

  it("rejects $ref", () => {
    expect(() =>
      jsonSchemaToZod({
        type: "object",
        properties: { a: { type: "string", $ref: "#/defs/x" } },
        required: ["a"],
      }),
    ).toThrow(SchemaConversionError);
  });
});
