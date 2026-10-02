/**
 * Hollow-result detection.
 *
 * The extractor's own prompt tells the model to "leave fields empty when
 * information is not present or you are uncertain", so a model that runs out of
 * output budget (or gives up mid-answer) can return a well-shaped payload whose
 * every field is empty. That is indistinguishable from success at the HTTP
 * layer — and it used to be cached, poisoning the cache for the TTL.
 *
 * A result is "hollow" when it contains no meaningful leaf anywhere:
 * empty/whitespace strings, empty arrays or arrays of hollow items, objects
 * whose values are all hollow, null/undefined. Numbers and booleans are
 * meaningful content (0 and false are real answers).
 */
export function isHollowResult(data: unknown): boolean {
  if (data === null || data === undefined) {
    return true;
  }
  if (typeof data === "string") {
    return data.trim().length === 0;
  }
  if (typeof data === "number" || typeof data === "boolean") {
    return false;
  }
  if (Array.isArray(data)) {
    return data.every(isHollowResult);
  }
  if (typeof data === "object") {
    const values = Object.values(data as Record<string, unknown>);
    return values.length === 0 || values.every(isHollowResult);
  }
  return false;
}
