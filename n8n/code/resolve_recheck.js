// Decide what a failed create really means, using the fresh lookup by submission ID.
const ctx = ctxOf('Check create');
const r = $input.first().json;
const failed = rpcFailure(ctx, r);
if (failed) return failed;

if (!r.result.length) {
  // Nothing was written. A transport failure is worth retrying; an Odoo error is not.
  return ctx.create_transport_error
    ? finish(ctx, 503, 'crm_unavailable', [`Opportunity not created: ${ctx.create_error}`], { retryable: true })
    : finish(ctx, 502, 'crm_error', [ctx.create_error]);
}

const crmId = r.result[0].id;
// A concurrent identical request won the race: the unique index rejected this one.
if (/x_submission_id|unique|duplicate key/i.test(ctx.create_error)) {
  return finish(ctx, 200, 'duplicate', [], { crm_id: crmId, verified: true });
}
// The create timed out after Odoo committed it: treat it as ours and verify it.
return go(ctx, { crm_id: crmId, recovered: true, call: readOpportunity(crmId) });
