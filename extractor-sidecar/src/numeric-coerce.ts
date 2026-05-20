import { z } from "zod";

import type { ValidationMode } from "./validation-mode.js";
import { VALIDATION_MODE_COERCE } from "./validation-mode.js";

/**
 * For web-extracted values: take leading numeric token from strings like "518 points".
 */
export function preprocessNumericInput(val: unknown): unknown {
  if (typeof val !== "string") {
    return val;
  }
  const trimmed = val.trim();
  const match = trimmed.match(/^-?\d+(?:\.\d+)?/);
  if (match) {
    return match[0];
  }
  return val;
}

export function zodNumberLeaf(
  mode: ValidationMode,
  integersOnly: boolean,
): z.ZodTypeAny {
  if (mode !== VALIDATION_MODE_COERCE) {
    return integersOnly ? z.number().int() : z.number();
  }
  const coerced = integersOnly
    ? z.coerce.number().int()
    : z.coerce.number();
  return z.preprocess(preprocessNumericInput, coerced);
}
