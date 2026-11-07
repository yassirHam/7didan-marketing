// Browser-side calls to this app's /api routes. Every call has a timeout and returns a typed result.
import type { ChatResponse, EnquiryRequest, EnquiryResponse, FunnelEvent } from "./contract";

export type Mode = "demo" | "live";
const modeOf = (res: Response): Mode => (res.headers.get("x-7didan-mode") === "live" ? "live" : "demo");

async function post(path: string, body: unknown, timeoutMs: number): Promise<Response> {
  return fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
}

export type ChatResult = { ok: true; data: ChatResponse; mode: Mode } | { ok: false; error: string };

export async function sendMessage(conversationId: string, message: string): Promise<ChatResult> {
  try {
    const res = await post("/api/chat", { conversation_id: conversationId, message }, 45_000);
    const data = await res.json().catch(() => null);
    if (!res.ok || !data || typeof data.answer !== "string") {
      return { ok: false, error: (data && typeof data.error === "string" && data.error) || "The assistant is not available right now." };
    }
    return { ok: true, data: { sources: [], offer_qualification: false, suggested_service: null, ...data }, mode: modeOf(res) };
  } catch (err) {
    const timedOut = err instanceof DOMException && err.name === "TimeoutError";
    return { ok: false, error: timedOut ? "The assistant took too long to answer." : "Connection problem. Check your network and try again." };
  }
}

/** Never throws. A network error or timeout is reported as retryable, because the same submission_id is safe to resend. */
export async function submitEnquiry(enquiry: EnquiryRequest): Promise<EnquiryResponse> {
  const fallback = (status: EnquiryResponse["status"], error: string): EnquiryResponse => ({
    status, submission_id: enquiry.submission_id, crm_id: null, verified: false, retryable: true, errors: [error],
  });
  try {
    const res = await post("/api/enquiries", enquiry, 120_000);
    const data = await res.json().catch(() => null);
    if (!data || typeof data.status !== "string") return fallback("bad_response", `Unexpected answer (HTTP ${res.status}).`);
    return {
      status: data.status,
      submission_id: data.submission_id ?? enquiry.submission_id,
      crm_id: typeof data.crm_id === "number" ? data.crm_id : null,
      verified: data.verified === true,
      retryable: data.retryable === true,
      errors: Array.isArray(data.errors) ? data.errors.map(String) : [],
    };
  } catch {
    return fallback("backend_unavailable", "No answer from the server.");
  }
}

/** Fire-and-forget funnel event. Uses sendBeacon when the page is closing. */
export function trackEvent(conversationId: string, event: FunnelEvent, closing = false): void {
  const body = JSON.stringify({ conversation_id: conversationId, event });
  if (closing && navigator.sendBeacon) {
    navigator.sendBeacon("/api/events", new Blob([body], { type: "application/json" }));
    return;
  }
  fetch("/api/events", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
}

export const newId = (): string => crypto.randomUUID();
