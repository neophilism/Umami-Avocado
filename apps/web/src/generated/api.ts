// Generated from the canonical FastAPI OpenAPI document. Do not edit.
// Contract SHA-256: 74c19a24be681ff8c1230eb058e07fa5f9d52365247ffc5fe18f22bec3b32302
export interface ErrorDetail {
  readonly code: "invalid_request" | "not_found" | "method_not_allowed" | "internal_error";
  readonly message: string;
}

export interface ErrorEnvelope {
  readonly error: ErrorDetail;
  readonly schema_version: "1.0";
}

export interface HealthResponse {
  readonly environment: string;
  readonly live_lab_orders_enabled: false;
  readonly schema_version: "1.0";
  readonly status: "ok";
}

export interface ReadinessResponse {
  readonly artifact_store_connected: false;
  readonly database_connected: false;
  readonly live_lab_orders_enabled: false;
  readonly schema_version: "1.0";
  readonly status: "foundation-only";
}

export type ResultOrigin = "SIMULATED" | "PHYSICAL";

type Schema = { $ref?: string; type?: string; title?: string; description?: string; const?: unknown; enum?: unknown[];
  properties?: Record<string, Schema>; required?: string[]; additionalProperties?: boolean;
  minLength?: number; maxLength?: number; pattern?: string };
const schemas: Record<string, Schema> = {"ErrorDetail":{"additionalProperties":false,"properties":{"code":{"enum":["invalid_request","not_found","method_not_allowed","internal_error"],"title":"Code","type":"string"},"message":{"maxLength":200,"minLength":1,"title":"Message","type":"string"}},"required":["code","message"],"title":"ErrorDetail","type":"object"},"ErrorEnvelope":{"additionalProperties":false,"properties":{"error":{"$ref":"#/components/schemas/ErrorDetail"},"schema_version":{"const":"1.0","title":"Schema Version","type":"string"}},"required":["schema_version","error"],"title":"ErrorEnvelope","type":"object"},"HealthResponse":{"additionalProperties":false,"properties":{"environment":{"maxLength":64,"minLength":1,"pattern":"^[a-z][a-z0-9_-]*$","title":"Environment","type":"string"},"live_lab_orders_enabled":{"const":false,"title":"Live Lab Orders Enabled","type":"boolean"},"schema_version":{"const":"1.0","title":"Schema Version","type":"string"},"status":{"const":"ok","title":"Status","type":"string"}},"required":["schema_version","live_lab_orders_enabled","status","environment"],"title":"HealthResponse","type":"object"},"ReadinessResponse":{"additionalProperties":false,"properties":{"artifact_store_connected":{"const":false,"title":"Artifact Store Connected","type":"boolean"},"database_connected":{"const":false,"title":"Database Connected","type":"boolean"},"live_lab_orders_enabled":{"const":false,"title":"Live Lab Orders Enabled","type":"boolean"},"schema_version":{"const":"1.0","title":"Schema Version","type":"string"},"status":{"const":"foundation-only","title":"Status","type":"string"}},"required":["schema_version","live_lab_orders_enabled","status","database_connected","artifact_store_connected"],"title":"ReadinessResponse","type":"object"},"ResultOrigin":{"description":"Provenance only. Neither value grants physical authorization.","enum":["SIMULATED","PHYSICAL"],"title":"ResultOrigin","type":"string"}};
const operations: Record<string, { path: string; response: string; errors: Record<string, {schema: string; code: string}> }> = {"get_health":{"errors":{"400":{"code":"invalid_request","schema":"ErrorEnvelope"},"404":{"code":"not_found","schema":"ErrorEnvelope"},"405":{"code":"method_not_allowed","schema":"ErrorEnvelope"},"500":{"code":"internal_error","schema":"ErrorEnvelope"}},"path":"/api/health","response":"HealthResponse"},"get_readiness":{"errors":{"400":{"code":"invalid_request","schema":"ErrorEnvelope"},"404":{"code":"not_found","schema":"ErrorEnvelope"},"405":{"code":"method_not_allowed","schema":"ErrorEnvelope"},"500":{"code":"internal_error","schema":"ErrorEnvelope"}},"path":"/api/readiness","response":"ReadinessResponse"}};
export const contractDigest = "74c19a24be681ff8c1230eb058e07fa5f9d52365247ffc5fe18f22bec3b32302";
const maxResponseBytes = 65536;

export class ProtocolError extends Error {
  readonly code = "invalid_response";
  constructor() { super("The service response does not match the API contract."); }
}
export class TransportError extends Error {
  readonly code = "transport_error";
  constructor() { super("The API request could not be completed."); }
}
export class ApiClientError extends Error {
  constructor(readonly status: number, readonly detail: ErrorEnvelope) {
    super("The API returned " + detail.error.code + ".");
  }
}

function valid(value: unknown, schema: Schema, depth = 0): boolean {
  if (depth > 32) return false;
  if (schema.$ref) {
    const target = schemas[schema.$ref.slice("#/components/schemas/".length)];
    return !!target && valid(value, target, depth + 1);
  }
  if (schema.type === "object") {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const object = value as Record<string, unknown>, properties = schema.properties ?? {};
    if ((schema.required ?? []).some(key => !Object.hasOwn(object, key))) return false;
    if (schema.additionalProperties === false && Object.keys(object).some(key => !Object.hasOwn(properties, key))) return false;
    return Object.entries(object).every(([key, item]) => !properties[key] || valid(item, properties[key], depth + 1));
  }
  if (schema.type === "string") {
    if (typeof value !== "string") return false;
    const length = Array.from(value).length;
    if (schema.minLength !== undefined && length < schema.minLength) return false;
    if (schema.maxLength !== undefined && length > schema.maxLength) return false;
    if (schema.pattern) {
      const match = new RegExp(schema.pattern).exec(value);
      if (!match || match[0] !== value) return false;
    }
  } else if (schema.type === "boolean") {
    if (typeof value !== "boolean") return false;
  } else return false;
  if (Object.hasOwn(schema, "const") && value !== schema.const) return false;
  if (schema.enum && !schema.enum.includes(value)) return false;
  return true;
}

export function validateResponse(name: string, value: unknown): boolean {
  return Object.hasOwn(schemas, name) && valid(value, schemas[name]);
}

async function jsonBody(response: Response): Promise<unknown> {
  async function reject(): Promise<never> {
    await response.body?.cancel().catch(() => undefined);
    throw new ProtocolError();
  }
  if (response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase() !== "application/json") return reject();
  const declared = response.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > maxResponseBytes)) return reject();
  if (!response.body) throw new ProtocolError();
  const reader = response.body.getReader(), chunks: Uint8Array[] = [];
  let size = 0, finished = false;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) { finished = true; break; }
      size += value.byteLength;
      if (size > maxResponseBytes) throw new ProtocolError();
      chunks.push(value);
    }
    const bytes = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    try { return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)); }
    catch { throw new ProtocolError(); }
  } finally {
    if (!finished) await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

function origin(value: string): string {
  if (value === "") return value;
  if (Array.from(value).some(character => character === "\\" || character.charCodeAt(0) <= 32 || character.charCodeAt(0) === 127)) throw new TypeError("Configure an API origin.");
  let url: URL;
  try { url = new URL(value); } catch { throw new TypeError("Configure an API origin."); }
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (url.username || url.password || url.search || url.hash || url.pathname !== "/" ||
      !(url.protocol === "https:" || (local && url.protocol === "http:"))) throw new TypeError("Configure an HTTPS or loopback API origin.");
  return url.origin;
}

export class ApiClient {
  private readonly base: string;
  constructor(private readonly options: {baseUrl?: string; fetch?: typeof fetch; timeoutMs?: number} = {}) {
    this.base = origin(options.baseUrl ?? "");
    if (options.timeoutMs !== undefined && (!Number.isInteger(options.timeoutMs) || options.timeoutMs < 1 || options.timeoutMs > 60000)) throw new TypeError("Use a timeout from 1 to 60000 milliseconds.");
  }
  private async request(operationId: string, signal?: AbortSignal): Promise<unknown> {
    const operation = operations[operationId], controller = new AbortController();
    const abort = () => controller.abort();
    const timer = setTimeout(abort, this.options.timeoutMs ?? 5000);
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) abort();
    try {
      const response = await (this.options.fetch ?? globalThis.fetch)(this.base + operation.path, {
        method: "GET", headers: {Accept: "application/json"}, redirect: "error",
        credentials: "omit", cache: "no-store", signal: controller.signal,
      });
      const body = await jsonBody(response);
      if (response.status === 200) {
        if (!validateResponse(operation.response, body)) throw new ProtocolError();
        return body;
      }
      const error = operation.errors[String(response.status)];
      if (!error || !validateResponse(error.schema, body)) throw new ProtocolError();
      const envelope = body as ErrorEnvelope;
      if (envelope.error.code !== error.code) throw new ProtocolError();
      throw new ApiClientError(response.status, envelope);
    } catch (error) {
      if (error instanceof ApiClientError || error instanceof ProtocolError) throw error;
      throw new TransportError();
    } finally { clearTimeout(timer); signal?.removeEventListener("abort", abort); }
  }
  async getHealth(signal?: AbortSignal): Promise<HealthResponse> {
    return await this.request("get_health", signal) as HealthResponse;
  }

  async getReadiness(signal?: AbortSignal): Promise<ReadinessResponse> {
    return await this.request("get_readiness", signal) as ReadinessResponse;
  }
}
