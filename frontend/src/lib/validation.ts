// Field rules. They mirror n8n/code/validate_enquiry.js so the visitor sees problems before sending;
// the workflow still validates everything again on the server side.
import { SERVICE_CATEGORIES, type ContactDetails, type QualificationAnswers } from "./contract";

export const LIMITS = {
  message: 2000,
  name: 120,
  company: 160,
  email: 254,
  serviceInterest: 120,
  need: 1000,
  optional: 500, // budget, requirements, timeline
} as const;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE = /^\+?[0-9 ().-]{6,20}$/;
const ID = /^[A-Za-z0-9-]{8,64}$/;

export type FieldErrors = Partial<Record<string, string>>;

const required = (v: string, max: number, label: string) =>
  !v.trim() ? `${label} is required.` : v.trim().length > max ? `${label} must be at most ${max} characters.` : null;
const optional = (v: string | null, max: number, label: string) =>
  v != null && v.trim().length > max ? `${label} must be at most ${max} characters.` : null;

export function validateNeed(q: Pick<QualificationAnswers, "service_interest" | "service_category" | "need">): FieldErrors {
  const e: FieldErrors = {};
  if (!SERVICE_CATEGORIES.some((c) => c.value === q.service_category)) e.service_category = "Choose a category.";
  const si = required(q.service_interest, LIMITS.serviceInterest, "The service");
  if (si) e.service_interest = si;
  const need = required(q.need, LIMITS.need, "Your need");
  if (need) e.need = need;
  return e;
}

export function validateRequirements(q: Pick<QualificationAnswers, "budget" | "requirements">): FieldErrors {
  const e: FieldErrors = {};
  const b = optional(q.budget, LIMITS.optional, "Budget");
  if (b) e.budget = b;
  const r = optional(q.requirements, LIMITS.optional, "Requirements");
  if (r) e.requirements = r;
  return e;
}

export function validateTimeline(q: Pick<QualificationAnswers, "timeline">): FieldErrors {
  const t = optional(q.timeline, LIMITS.optional, "Timeline");
  return t ? { timeline: t } : {};
}

export function validateContact(c: ContactDetails, consent: boolean): FieldErrors {
  const e: FieldErrors = {};
  const name = required(c.name, LIMITS.name, "Your name");
  if (name) e.name = name;
  const company = required(c.company, LIMITS.company, "Company");
  if (company) e.company = company;
  if (!EMAIL.test(c.email.trim()) || c.email.trim().length > LIMITS.email) e.email = "Enter a valid email address.";
  if (c.phone && c.phone.trim() && !PHONE.test(c.phone.trim())) e.phone = "Enter a valid phone number (digits, spaces, + ( ) . -).";
  if (!consent) e.consent = "Tick the box so we can send your enquiry.";
  return e;
}

export const isId = (v: unknown): v is string => typeof v === "string" && ID.test(v);
export const hasErrors = (e: FieldErrors) => Object.keys(e).length > 0;

/**
 * The workflow names fields in its messages ("contact.email is not a valid email address.").
 * Map them back to the form fields so the visitor sees each message next to the right input.
 */
export function fieldErrorsFromServer(errors: string[]): { fields: FieldErrors; other: string[] } {
  const fields: FieldErrors = {};
  const other: string[] = [];
  for (const msg of errors) {
    const m = /^(contact|qualification)\.(\w+)/.exec(msg);
    if (m) fields[m[2]] = msg.replace(/^(contact|qualification)\.\w+\s*/, "").replace(/^is /, "This is ").replace(/^must /, "This must ");
    else other.push(msg);
  }
  return { fields, other };
}
