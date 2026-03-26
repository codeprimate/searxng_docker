/**
 * Stable JSON serialization with sorted object keys (for cache keys).
 */
export function canonicalJson(value: unknown): string {
  if (value === null) {
    return "null";
  }
  if (typeof value === "object" && !Array.isArray(value) && value !== null) {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    const inner = keys
      .map((k) => `${JSON.stringify(k)}:${canonicalJson(obj[k])}`)
      .join(",");
    return `{${inner}}`;
  }
  if (Array.isArray(value)) {
    return `[${value.map((v) => canonicalJson(v)).join(",")}]`;
  }
  return JSON.stringify(value);
}
