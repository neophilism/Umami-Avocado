import { describe, expect, it } from "vitest";
import examples from "../../../contracts/client-examples.json";
import { ApiClient, ApiClientError, ProtocolError, TransportError, validateResponse } from "./generated/api";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "Content-Type": "application/json; charset=utf-8" },
});

describe("generated API client", () => {
  it("uses canonical read-only routes and explicit credential/cache/redirect policy", async () => {
    const calls: Array<{url: string; init?: RequestInit}> = [];
    const fetcher: typeof fetch = async (url, init) => {
      calls.push({url: String(url), init});
      return json(String(url).endsWith("health") ? examples.health : examples.readiness);
    };
    const client = new ApiClient({baseUrl: "https://synthetic.example", fetch: fetcher});
    expect(await client.getHealth()).toEqual(examples.health);
    expect(await client.getReadiness()).toEqual(examples.readiness);
    expect(calls.map(call => call.url)).toEqual([
      "https://synthetic.example/api/health", "https://synthetic.example/api/readiness",
    ]);
    for (const call of calls) {
      expect(call.init).toMatchObject({method: "GET", credentials: "omit", cache: "no-store", redirect: "error"});
      expect(call.init?.body).toBeUndefined();
    }
  });

  for (const [index, body] of examples.invalidHealth.entries()) {
    it(`rejects shared invalid health response ${index}`, async () => {
      expect(validateResponse("HealthResponse", body)).toBe(false);
      await expect(new ApiClient({fetch: async () => json(body)}).getHealth()).rejects.toBeInstanceOf(ProtocolError);
    });
  }

  it("retains distinct provenance labels and rejects unknown model/schema values", () => {
    expect(validateResponse("ResultOrigin", "SIMULATED")).toBe(true);
    expect(validateResponse("ResultOrigin", "PHYSICAL")).toBe(true);
    expect(validateResponse("ResultOrigin", "simulated")).toBe(false);
    expect(validateResponse("UnknownFutureModel", {})).toBe(false);
    expect(validateResponse("constructor", {})).toBe(false);
    expect(validateResponse("ReadinessResponse", {...examples.readiness, database_connected: true})).toBe(false);
  });

  it("returns typed API errors without including the provider message in Error text", async () => {
    const envelope = {schema_version: "1.0", error: {code: "internal_error", message: "private-fixture"}};
    const client = new ApiClient({fetch: async () => json(envelope, 500)});
    try { await client.getHealth(); throw new Error("Expected a rejection"); }
    catch (error) {
      expect(error).toBeInstanceOf(ApiClientError);
      const typed = error as ApiClientError;
      expect(typed.status).toBe(500);
      expect(typed.detail).toEqual(envelope);
      expect(typed.message).not.toContain("private-fixture");
    }
    await expect(new ApiClient({fetch: async () => json(envelope, 404)}).getHealth()).rejects.toBeInstanceOf(ProtocolError);
    await expect(new ApiClient({fetch: async () => json(envelope, 503)}).getHealth()).rejects.toBeInstanceOf(ProtocolError);
  });

  for (const [name, make] of [
    ["malformed JSON", () => new Response("not-json", {headers: {"Content-Type": "application/json"}})],
    ["invalid UTF-8", () => new Response(new Uint8Array([255]), {headers: {"Content-Type": "application/json"}})],
    ["wrong content type", () => new Response("private-fixture", {headers: {"Content-Type": "text/html"}})],
    ["empty body", () => new Response(null, {headers: {"Content-Type": "application/json"}})],
    ["oversized body", () => new Response(" ".repeat(65537), {headers: {"Content-Type": "application/json"}})],
    ["unknown status", () => json(examples.health, 302)],
  ] as const) {
    it(`rejects ${name}`, async () => {
      await expect(new ApiClient({fetch: async () => make()}).getHealth()).rejects.toBeInstanceOf(ProtocolError);
    });
  }

  it("cancels early rejected and oversized streams instead of downloading them", async () => {
    const headerCases: Record<string, string>[] = [
      {"Content-Type": "text/html"},
      {"Content-Type": "application/json", "Content-Length": "65537"},
      {"Content-Type": "application/json", "Content-Length": "invalid"},
      {"Content-Type": "application/json"},
    ];
    for (const headers of headerCases) {
      let cancelled = false;
      const body = new ReadableStream<Uint8Array>({
        start(controller) { controller.enqueue(new Uint8Array(65537)); },
        cancel() { cancelled = true; },
      });
      const client = new ApiClient({fetch: async () => new Response(body, {headers})});
      await expect(client.getHealth()).rejects.toBeInstanceOf(ProtocolError);
      expect(cancelled).toBe(true);
    }
  });

  it("does not retry or reveal dependency failure details", async () => {
    let calls = 0;
    const client = new ApiClient({fetch: async () => { calls++; throw new Error("private-fixture"); }});
    await expect(client.getHealth()).rejects.toBeInstanceOf(TransportError);
    await expect(client.getHealth()).rejects.not.toThrow("private-fixture");
    expect(calls).toBe(2); // Exactly one attempt for each explicit caller request.
  });

  it("honors timeout and already-aborted caller cancellation", async () => {
    const fetcher: typeof fetch = (_url, init) => new Promise<Response>((_resolve, reject) => {
      const fail = () => reject(new DOMException("Aborted", "AbortError"));
      if (init?.signal?.aborted) fail();
      else init?.signal?.addEventListener("abort", fail, {once: true});
    });
    await expect(new ApiClient({fetch: fetcher, timeoutMs: 5}).getHealth()).rejects.toBeInstanceOf(TransportError);
    const abort = new AbortController(); abort.abort();
    await expect(new ApiClient({fetch: fetcher}).getHealth(abort.signal)).rejects.toBeInstanceOf(TransportError);
  });

  it("rejects unsafe configuration before fetching", () => {
    for (const baseUrl of ["http://remote.example", "https://user:private@example.test", "https://example.test/path",
      "https://example.test?x=1", "https://example.test#fragment", "https://example.test/\n", "https:\\example.test"]) {
      expect(() => new ApiClient({baseUrl})).toThrow(TypeError);
    }
    for (const timeoutMs of [0, -1, 60001, NaN, Infinity, 1.5]) {
      expect(() => new ApiClient({timeoutMs})).toThrow(TypeError);
    }
  });
});
