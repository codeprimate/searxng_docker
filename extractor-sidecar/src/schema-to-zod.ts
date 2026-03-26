/**
 * JSON Schema (v1 subset) → Zod. Hand-rolled for supported subset only.
 */
import { z } from "zod";

export const ERR_NULLABLE_KEYWORD =
  "JSON Schema keyword nullable is not supported in v1; use type: [\"T\", \"null\"] instead";
export const ERR_ADDITIONAL_PROPERTIES_TRUE =
  "additionalProperties: true is not supported; omit or set to false for strict objects";
export const ERR_UNSUPPORTED_KEY = (key: string) =>
  `Unsupported JSON Schema keyword or property: ${key}`;
export const ERR_UNSUPPORTED_TYPE = (t: string) =>
  `Unsupported JSON Schema type: ${t}`;

export class SchemaConversionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SchemaConversionError";
  }
}

const OBJECT_KEYS = new Set([
  "type",
  "properties",
  "required",
  "additionalProperties",
  "description",
]);
const ARRAY_KEYS = new Set(["type", "items", "description"]);
const LEAF_KEYS = new Set(["type", "description"]);

function assertAllowedKeys(
  obj: Record<string, unknown>,
  allowed: Set<string>,
  ctx: string,
): void {
  for (const k of Object.keys(obj)) {
    if (!allowed.has(k)) {
      throw new SchemaConversionError(
        `${ERR_UNSUPPORTED_KEY(k)} (at ${ctx})`,
      );
    }
  }
}

function assertNoNullableKeyword(node: unknown, path: string): void {
  if (node === null || typeof node !== "object") {
    return;
  }
  if (Array.isArray(node)) {
    node.forEach((item, i) =>
      assertNoNullableKeyword(item, `${path}[${i}]`),
    );
    return;
  }
  const rec = node as Record<string, unknown>;
  if (Object.prototype.hasOwnProperty.call(rec, "nullable")) {
    throw new SchemaConversionError(ERR_NULLABLE_KEYWORD);
  }
  for (const k of Object.keys(rec)) {
    assertNoNullableKeyword(rec[k], `${path}.${k}`);
  }
}

type ParsedSimpleType =
  | "string"
  | "number"
  | "integer"
  | "boolean"
  | "object"
  | "array";

interface ParsedType {
  base: ParsedSimpleType;
  nullable: boolean;
}

function parseTypeField(
  schema: Record<string, unknown>,
  ctx: string,
): ParsedType {
  const t = schema.type;
  if (typeof t === "string") {
    const base = t as ParsedSimpleType;
    if (
      !["string", "number", "integer", "boolean", "object", "array"].includes(
        base,
      )
    ) {
      throw new SchemaConversionError(`${ERR_UNSUPPORTED_TYPE(t)} (at ${ctx})`);
    }
    return { base, nullable: false };
  }
  if (Array.isArray(t)) {
    const hasNull = t.includes("null");
    const rest = t.filter((x) => x !== "null") as string[];
    if (!hasNull || rest.length !== 1) {
      throw new SchemaConversionError(
        `type arrays must be exactly [\"<type>\", \"null\"] in v1 (at ${ctx})`,
      );
    }
    const base = rest[0] as ParsedSimpleType;
    if (
      !["string", "number", "integer", "boolean", "object", "array"].includes(
        base,
      )
    ) {
      throw new SchemaConversionError(`${ERR_UNSUPPORTED_TYPE(rest[0])} (at ${ctx})`);
    }
    return { base, nullable: true };
  }
  throw new SchemaConversionError(`Missing or invalid type (at ${ctx})`);
}

function wrapNullable<T extends z.ZodTypeAny>(
  schema: T,
  nullable: boolean,
): z.ZodTypeAny {
  if (!nullable) {
    return schema;
  }
  return z.union([schema, z.null()]);
}

function buildObjectSchema(
  schema: Record<string, unknown>,
  ctx: string,
): z.ZodObject<Record<string, z.ZodTypeAny>> {
  assertAllowedKeys(schema, OBJECT_KEYS, ctx);
  const ap = schema.additionalProperties;
  if (ap === true) {
    throw new SchemaConversionError(ERR_ADDITIONAL_PROPERTIES_TRUE);
  }
  if (ap !== undefined && ap !== false) {
    throw new SchemaConversionError(
      `${ERR_UNSUPPORTED_KEY("additionalProperties")} (at ${ctx})`,
    );
  }
  const props = schema.properties;
  if (props === undefined || typeof props !== "object" || props === null || Array.isArray(props)) {
    throw new SchemaConversionError(
      `object type requires properties (at ${ctx})`,
    );
  }
  const propRec = props as Record<string, unknown>;
  const required = new Set(
    Array.isArray(schema.required)
      ? (schema.required as string[])
      : [],
  );
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const key of Object.keys(propRec)) {
    const child = jsonSchemaToZodInner(propRec[key], `${ctx}.properties.${key}`);
    shape[key] = required.has(key) ? child : child.optional();
  }
  let obj = z.object(shape).strict();
  const desc = schema.description;
  if (typeof desc === "string" && desc.length > 0) {
    obj = obj.describe(desc);
  }
  return obj;
}

function buildArraySchema(
  schema: Record<string, unknown>,
  ctx: string,
): z.ZodArray<z.ZodTypeAny> {
  assertAllowedKeys(schema, ARRAY_KEYS, ctx);
  if (schema.items === undefined) {
    throw new SchemaConversionError(`array type requires items (at ${ctx})`);
  }
  const itemSchema = jsonSchemaToZodInner(schema.items, `${ctx}.items`);
  let arr = z.array(itemSchema);
  const desc = schema.description;
  if (typeof desc === "string" && desc.length > 0) {
    arr = arr.describe(desc);
  }
  return arr;
}

function jsonSchemaToZodInner(node: unknown, ctx: string): z.ZodTypeAny {
  if (node === null || typeof node !== "object" || Array.isArray(node)) {
    throw new SchemaConversionError(`Schema must be an object (at ${ctx})`);
  }
  const schema = node as Record<string, unknown>;
  const { base, nullable } = parseTypeField(schema, ctx);

  let inner: z.ZodTypeAny;
  switch (base) {
    case "string": {
      assertAllowedKeys(schema, LEAF_KEYS, ctx);
      inner = z.string();
      const d = schema.description;
      if (typeof d === "string" && d.length > 0) {
        inner = inner.describe(d);
      }
      break;
    }
    case "number": {
      assertAllowedKeys(schema, LEAF_KEYS, ctx);
      inner = z.number();
      const d = schema.description;
      if (typeof d === "string" && d.length > 0) {
        inner = inner.describe(d);
      }
      break;
    }
    case "integer": {
      assertAllowedKeys(schema, LEAF_KEYS, ctx);
      inner = z.number().int();
      const d = schema.description;
      if (typeof d === "string" && d.length > 0) {
        inner = inner.describe(d);
      }
      break;
    }
    case "boolean": {
      assertAllowedKeys(schema, LEAF_KEYS, ctx);
      inner = z.boolean();
      const d = schema.description;
      if (typeof d === "string" && d.length > 0) {
        inner = inner.describe(d);
      }
      break;
    }
    case "object": {
      inner = buildObjectSchema(schema, ctx);
      break;
    }
    case "array": {
      inner = buildArraySchema(schema, ctx);
      break;
    }
    default:
      throw new SchemaConversionError(ERR_UNSUPPORTED_TYPE(base));
  }

  return wrapNullable(inner, nullable);
}

/**
 * Convert a JSON Schema (v1 subset) object to a Zod schema.
 * @param root — parsed JSON (object) for `json_schema` from the request body
 */
export function jsonSchemaToZod(root: unknown): z.ZodTypeAny {
  assertNoNullableKeyword(root, "$");
  if (root === null || typeof root !== "object" || Array.isArray(root)) {
    throw new SchemaConversionError("json_schema must be a JSON object");
  }
  return jsonSchemaToZodInner(root, "$");
}
