import type { EnquiryRequest, EnquiryResponse } from "@/lib/contract";
import { demoEnquiry } from "@/lib/server/demo";
import { backendUrl, forward, json, readJson } from "@/lib/server/upstream";
import { isId } from "@/lib/validation";

const text = (v: unknown): string => (typeof v === "string" ? v : "");
const textOrNull = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v.trim() : null);

/**
 * Only the contract's fields are passed on, with their types fixed. The content itself is
 * validated by the backend and again by the n8n workflow.
 */
function toEnquiry(body: Record<string, unknown>): EnquiryRequest | null {
  const q = (body.qualification ?? {}) as Record<string, unknown>;
  const c = (body.contact ?? {}) as Record<string, unknown>;
  if (!isId(body.submission_id) || !isId(body.conversation_id)) return null;
  return {
    submission_id: body.submission_id,
    conversation_id: body.conversation_id,
    qualification: {
      service_interest: text(q.service_interest).trim(),
      service_category: text(q.service_category) as EnquiryRequest["qualification"]["service_category"],
      need: text(q.need).trim(),
      budget: textOrNull(q.budget),
      requirements: textOrNull(q.requirements),
      timeline: textOrNull(q.timeline),
    },
    contact: { name: text(c.name).trim(), company: text(c.company).trim(), email: text(c.email).trim(), phone: textOrNull(c.phone) },
    consent: body.consent === true,
  };
}

const unavailable = (id: string | null): EnquiryResponse => ({
  status: "backend_unavailable", submission_id: id, crm_id: null, verified: false, retryable: true,
  errors: ["The backend did not answer. Retrying with the same submission ID is safe."],
});

export async function POST(req: Request) {
  const body = await readJson(req);
  if (!body) {
    return json({ status: "invalid", submission_id: null, crm_id: null, verified: false, retryable: false,
      errors: ["The request must be a JSON object."] } satisfies EnquiryResponse, 422);
  }
  const enquiry = toEnquiry(body);
  if (!enquiry) {
    return json({ status: "invalid", submission_id: null, crm_id: null, verified: false, retryable: false,
      errors: ["submission_id and conversation_id must be 8-64 letters, digits or dashes."] } satisfies EnquiryResponse, 422);
  }

  if (!backendUrl()) {
    const r = await demoEnquiry(enquiry);
    return json(r.body, r.status);
  }

  // The backend may retry n8n up to 3 times, so allow it time before giving up.
  const r = await forward("/api/enquiries", enquiry, 100_000);
  if (!r.ok) return json(unavailable(enquiry.submission_id), 503);
  return json(r.body, r.status);
}
