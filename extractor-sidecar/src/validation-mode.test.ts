import { describe, expect, it } from "vitest";

import {
  DEFAULT_VALIDATION_MODE,
  parseValidationMode,
  VALIDATION_MODE_COERCE,
  VALIDATION_MODE_STRICT,
} from "./validation-mode.js";

describe("parseValidationMode", () => {
  it("defaults to coerce", () => {
    expect(parseValidationMode(undefined)).toBe(DEFAULT_VALIDATION_MODE);
    expect(DEFAULT_VALIDATION_MODE).toBe(VALIDATION_MODE_COERCE);
  });

  it("accepts strict and coerce", () => {
    expect(parseValidationMode("strict")).toBe(VALIDATION_MODE_STRICT);
    expect(parseValidationMode("COERCE")).toBe(VALIDATION_MODE_COERCE);
  });

  it("rejects unknown modes", () => {
    expect(() => parseValidationMode("sanitize")).toThrow(/strict|coerce/);
  });
});
