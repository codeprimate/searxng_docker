import { describe, expect, it } from "vitest";

import {
  SchemaConversionError,
  jsonSchemaToZod,
} from "./schema-to-zod.js";
import { VALIDATION_MODE_COERCE, VALIDATION_MODE_STRICT } from "./validation-mode.js";

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

  it("coerce mode (default) parses numeric strings for integer fields", () => {
    const zod = jsonSchemaToZod({
      type: "object",
      properties: {
        points: { type: "integer" },
      },
      required: ["points"],
    });
    expect(zod.parse({ points: "518" })).toEqual({ points: 518 });
    expect(zod.parse({ points: "518 points" })).toEqual({ points: 518 });
  });

  it("strict mode rejects numeric strings for integer fields", () => {
    const zod = jsonSchemaToZod(
      {
        type: "object",
        properties: {
          points: { type: "integer" },
        },
        required: ["points"],
      },
      { validationMode: VALIDATION_MODE_STRICT },
    );
    expect(zod.parse({ points: 518 })).toEqual({ points: 518 });
    expect(() => zod.parse({ points: "518" })).toThrow();
  });

  it("defaults to coerce mode when option omitted", () => {
    const zod = jsonSchemaToZod(
      {
        type: "object",
        properties: { n: { type: "integer" } },
        required: ["n"],
      },
      { validationMode: VALIDATION_MODE_COERCE },
    );
    expect(zod.parse({ n: "42" })).toEqual({ n: 42 });
  });
});
