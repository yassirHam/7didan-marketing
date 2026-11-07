// Authenticate the backend, validate the enquiry and map it to Odoo opportunity fields.
// Invalid data never reaches Odoo.
const CATEGORIES = ['connectivity', 'mobile', 'cloud', 'cybersecurity', 'collaboration', 'other'];

const req = $input.first().json;
const body = req.body && typeof req.body === 'object' ? req.body : {};
const ctx = {
  started_ms: Date.now(),
  submission_id: typeof body.submission_id === 'string' ? body.submission_id.slice(0, 64) : null,
};

if (!$env.WEBHOOK_TOKEN || (req.headers || {})['x-7didan-token'] !== $env.WEBHOOK_TOKEN) {
  return finish(ctx, 401, 'unauthorized', ['Missing or invalid X-7didan-Token header.']);
}

const isText = (v, max) => typeof v === 'string' && v.trim() !== '' && v.trim().length <= max;
const isOptionalText = (v, max) => v == null || (typeof v === 'string' && v.trim().length <= max);
const contact = body.contact || {};
const q = body.qualification || {};

const checks = [
  [/^[A-Za-z0-9-]{8,64}$/.test(String(body.submission_id || '')), 'submission_id must be 8-64 letters, digits or dashes.'],
  [isText(contact.name, 120), 'contact.name is required (max 120 characters).'],
  [isText(contact.company, 160), 'contact.company is required (max 160 characters).'],
  [typeof contact.email === 'string' && contact.email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(contact.email),
    'contact.email is not a valid email address.'],
  [contact.phone == null || (typeof contact.phone === 'string' && /^\+?[0-9 ().-]{6,20}$/.test(contact.phone)),
    'contact.phone is not a valid phone number.'],
  [isText(q.service_interest, 120), 'qualification.service_interest is required (max 120 characters).'],
  [CATEGORIES.includes(q.service_category), `qualification.service_category must be one of: ${CATEGORIES.join(', ')}.`],
  [isText(q.need, 1000), 'qualification.need is required (max 1000 characters).'],
  ...['budget', 'requirements', 'timeline'].map((k) => [isOptionalText(q[k], 500), `qualification.${k} must be text or null.`]),
  [Number.isInteger(body.lead_score) && body.lead_score >= 0 && body.lead_score <= 100, 'lead_score must be an integer from 0 to 100.'],
  [isOptionalText(body.conversation_summary, 4000), 'conversation_summary must be text (max 4000 characters).'],
  [isOptionalText(body.conversation_id, 64), 'conversation_id must be text (max 64 characters).'],
];
const errors = checks.filter(([ok]) => !ok).map(([, message]) => message);
const consentMissing = body.consent !== true;
if (consentMissing) errors.push('consent must be true: the contact has not agreed to be contacted.');
if (errors.length) {
  return finish(ctx, 422, consentMissing && errors.length === 1 ? 'consent_declined' : 'invalid', errors);
}

// Unanswered qualification questions are stored as "Unknown", never guessed.
const clean = (v) => (typeof v === 'string' && v.trim() ? v.trim() : null);
const escapeHtml = (s) => s.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
const answers = { budget: clean(q.budget), requirements: clean(q.requirements), timeline: clean(q.timeline) };
const status = Object.values(answers).includes(null) ? 'partial'
  : body.lead_score >= QUALIFIED_SCORE ? 'qualified' : 'not_qualified';
const summary = clean(body.conversation_summary);

return go(ctx, {
  category: q.service_category,
  values: {
    type: 'opportunity',
    name: `${contact.company.trim()} - ${q.service_interest.trim()}`,
    partner_name: contact.company.trim(),
    contact_name: contact.name.trim(),
    email_from: contact.email.trim().toLowerCase(),
    phone: clean(contact.phone) || false,
    // Stored as escaped text: the summary comes from a chat and is untrusted.
    description: summary ? `<p>${escapeHtml(summary)}</p>` : false,
    x_submission_id: ctx.submission_id,
    x_conversation_id: clean(body.conversation_id) || false,
    x_service_interest: q.service_interest.trim(),
    x_need: q.need.trim(),
    x_budget: answers.budget || 'Unknown',
    x_requirements: answers.requirements || 'Unknown',
    x_timeline: answers.timeline || 'Unknown',
    x_lead_score: body.lead_score,
    x_qualification_status: status,
    x_consent: true,
  },
});
