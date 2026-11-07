// On success, read the record back. On failure or timeout the create may still have been
// committed, so look the submission up again before anyone retries (route "recheck").
const ctx = ctxOf('Build opportunity');
const r = $input.first().json;

if (!r.error && Number.isInteger(r.result)) return go(ctx, { crm_id: r.result, call: readOpportunity(r.result) });

return [{
  json: {
    ...ctx,
    route: 'recheck',
    create_error: failureOf(r) || 'Unexpected response from Odoo create.',
    create_transport_error: isTransport(r),
    call: findSubmission(ctx.submission_id),
  },
}];
