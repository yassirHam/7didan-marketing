import "server-only";

// Server-side helpers for the /api routes: read the request safely, then either forward it to the
// FastAPI backend (BACKEND_URL set) or let the demo backend answer.

const MAX_BODY = 32 * 1024;

export type Mode = "demo" | "live";
export const backendUrl = (): string | null => process.env.BACKEND_URL?.replace(/\/+$/, "") || null;
export const modeOf = (): Mode => (backendUrl() ? "live" : "demo");

export function json(body: unknown, status = 200): Response {
  return Response.json(body, {
    status,
    headers: { "Cache-Control": "no-store", "X-7didan-Mode": modeOf() },
  });
}

/** Parse a JSON object body, refusing anything large or malformed. */
export async function readJson(req: Request): Promise<Record<string, unknown> | null> {
  if (!(req.headers.get("content-type") || "").includes("application/json")) return null;
  const text = await req.text();
  if (text.length > MAX_BODY) return null;
  try {
    const value = JSON.parse(text);
    return value && typeof value === "object" && !Array.isArray(value) ? value : null;
  } catch {
    return null;
  }
}

export type Forwarded = { ok: true; status: number; body: unknown } | { ok: false; reason: "timeout" | "unreachable" | "bad_response" };

/** POST to the FastAPI backend. Only JSON responses are passed back to the browser. */
export async function forward(path: string, body: unknown, timeoutMs: number): Promise<Forwarded> {
  try {
    const res = await fetch(`${backendUrl()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });
    if (res.status === 204) return { ok: true, status: 204, body: null };
    const data = await res.json().catch(() => undefined);
    return data === undefined ? { ok: false, reason: "bad_response" } : { ok: true, status: res.status, body: data };
  } catch (err) {
    const timeout = err instanceof DOMException && err.name === "TimeoutError";
    return { ok: false, reason: timeout ? "timeout" : "unreachable" };
  }
}
