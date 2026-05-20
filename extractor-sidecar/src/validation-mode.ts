export const VALIDATION_MODE_STRICT = "strict";
export const VALIDATION_MODE_COERCE = "coerce";

export type ValidationMode =
  | typeof VALIDATION_MODE_STRICT
  | typeof VALIDATION_MODE_COERCE;

export const DEFAULT_VALIDATION_MODE: ValidationMode = VALIDATION_MODE_COERCE;

const ALLOWED_MODES: ReadonlySet<string> = new Set([
  VALIDATION_MODE_STRICT,
  VALIDATION_MODE_COERCE,
]);

export const ENV_EXTRACT_VALIDATION_MODE = "EXTRACT_VALIDATION_MODE";

export function parseValidationMode(
  raw: string | undefined,
  envName: string = ENV_EXTRACT_VALIDATION_MODE,
): ValidationMode {
  if (raw === undefined || raw.trim() === "") {
    return DEFAULT_VALIDATION_MODE;
  }
  const normalized = raw.trim().toLowerCase();
  if (!ALLOWED_MODES.has(normalized)) {
    throw new Error(
      `${envName} must be "${VALIDATION_MODE_STRICT}" or "${VALIDATION_MODE_COERCE}"`,
    );
  }
  return normalized as ValidationMode;
}
