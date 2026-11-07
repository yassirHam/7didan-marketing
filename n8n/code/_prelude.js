// ── Shared helpers. build_workflow.py prepends this file to every Code node. ──
// Every Code node returns one item. route "continue" moves to the next step;
// route "done" goes straight to the webhook response with http_status and outcome.
const QUALIFIED_SCORE = 60;
const READ_FIELDS = [
  'type', 'stage_id', 'source_id', 'tag_ids', 'email_from', 'x_submission_id', 'x_service_interest',
  'x_need', 'x_budget', 'x_requirements', 'x_timeline', 'x_lead_score', 'x_qualification_status', 'x_consent',
];

const ctxOf = (node) => $(node).first().json;
const go = (ctx, patch = {}) => [{ json: { ...ctx, ...patch, route: 'continue' } }];
const finish = (ctx, httpStatus, outcome, errors = [], extra = {}) => [
  { json: { ...ctx, ...extra, route: 'done', http_status: httpStatus, outcome, errors } },
];

// HTTP nodes run with "continue on error": a failed call arrives as { error }.
// Odoo JSON-RPC errors also arrive as { error }, but inside a JSON-RPC envelope.
const failureOf = (r) => {
  if (!r || !r.error) return null;
  const e = r.error;
  return typeof e === 'string' ? e : (e.data && e.data.message) || e.message || JSON.stringify(e);
};
const isTransport = (r) => Boolean(r && r.error) && r.jsonrpc === undefined;
const rpcFailure = (ctx, r) => {
  if (!r || !r.error) return null;
  const transport = isTransport(r);
  return finish(ctx, transport ? 503 : 502, transport ? 'crm_unavailable' : 'crm_error',
    [failureOf(r)], { retryable: transport });
};

const findSubmission = (submissionId) => ({
  model: 'crm.lead', method: 'search_read',
  args: [[['x_submission_id', '=', submissionId]]],
  kwargs: { fields: ['id'], limit: 1, context: { active_test: false } },
});
const readOpportunity = (id) => ({ model: 'crm.lead', method: 'read', args: [[id]], kwargs: { fields: READ_FIELDS } });
// ── end of shared helpers ──
