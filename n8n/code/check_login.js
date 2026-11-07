// Result of the Odoo login with the restricted integration account.
const ctx = ctxOf('Validate enquiry');
const r = $input.first().json;

if (isTransport(r)) {
  return finish(ctx, 503, 'crm_unavailable', [`Odoo is unreachable: ${failureOf(r)}`], { retryable: true });
}
if (r.error) return finish(ctx, 502, 'crm_error', [failureOf(r)]);
if (!r.result) return finish(ctx, 502, 'crm_auth_failed', ['Odoo rejected the integration credentials.']);

// Idempotency, step 1: look for an opportunity that already carries this submission ID.
return go(ctx, { uid: r.result, call: findSubmission(ctx.submission_id) });
