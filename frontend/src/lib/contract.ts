// API contract between this frontend and the FastAPI backend (see docs/frontend_api.md).
// The browser only talks to this app's /api routes; they forward to BACKEND_URL or answer in demo mode.

export const SERVICE_CATEGORIES = [
  { value: "connectivity", label: "Connectivity", hint: "Business internet, fibre, links between sites" },
  { value: "mobile", label: "Mobile", hint: "Lines and data for your team" },
  { value: "cloud", label: "Cloud", hint: "Hosting, storage, servers" },
  { value: "cybersecurity", label: "Cybersecurity", hint: "Firewalls, protection, monitoring" },
  { value: "collaboration", label: "Collaboration", hint: "Meetings, messaging, telephony" },
  { value: "other", label: "Something else", hint: "Not sure which category" },
] as const;
export type ServiceCategory = (typeof SERVICE_CATEGORIES)[number]["value"];

// Timeline choices offered in question 3. The visitor can also type their own answer.
export const TIMELINE_CHOICES = ["As soon as possible", "Within 30 days", "Within 3 months", "Within 6 months", "Later, no rush"] as const;

// ── POST /api/chat ──────────────────────────────────────────────────────────
export interface ChatRequest {
  conversation_id: string;
  message: string;
}
export interface Source {
  title: string;
  section: string | null;
  url: string | null;
  retrieved_at: string | null; // ISO date the document was collected
}
export interface ChatResponse {
  answer: string;
  status: "answered" | "abstained";
  sources: Source[];
  offer_qualification: boolean;
  suggested_service: { service_interest: string; service_category: ServiceCategory } | null;
}

// ── POST /api/enquiries ─────────────────────────────────────────────────────
export interface QualificationAnswers {
  service_interest: string;
  service_category: ServiceCategory;
  need: string;
  budget: string | null; // null = the visitor did not answer; stored as "Unknown"
  requirements: string | null;
  timeline: string | null;
}
export interface ContactDetails {
  name: string;
  company: string;
  email: string;
  phone: string | null;
}
export interface EnquiryRequest {
  // Generated once per enquiry in the browser and reused on every retry (idempotency key).
  submission_id: string;
  conversation_id: string;
  qualification: QualificationAnswers;
  contact: ContactDetails;
  consent: boolean;
}
// Statuses from the n8n workflow (docs/crm_integration.md), plus two the frontend adds itself.
export type EnquiryStatus =
  | "created"
  | "duplicate"
  | "invalid"
  | "consent_declined"
  | "unauthorized"
  | "crm_auth_failed"
  | "crm_error"
  | "verification_failed"
  | "crm_unavailable"
  | "crm_not_configured"
  | "backend_unavailable" // this app could not reach the backend, or it timed out
  | "bad_response"; // the backend answered with something that is not the contract
export interface EnquiryResponse {
  status: EnquiryStatus;
  submission_id: string | null;
  crm_id: number | null;
  verified: boolean;
  retryable: boolean;
  errors: string[];
}

// ── POST /api/events ────────────────────────────────────────────────────────
// Funnel events the backend cannot see by itself. It writes them to reporting.conversation_events.
export const FUNNEL_EVENTS = ["qualification_started", "qualification_completed", "abandoned"] as const;
export type FunnelEvent = (typeof FUNNEL_EVENTS)[number];
export interface EventRequest {
  conversation_id: string;
  event: FunnelEvent;
}

/** The interface may only show success when this is true. */
export function isVerifiedSuccess(r: EnquiryResponse): boolean {
  return (r.status === "created" || r.status === "duplicate") && r.verified === true;
}
