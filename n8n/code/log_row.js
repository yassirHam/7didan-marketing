// One reporting.crm_transactions row per request (the response has already been sent).
const j = $input.first().json;
return [{
  json: {
    received_at: new Date(j.started_ms).toISOString(),
    submission_id: j.submission_id,
    outcome: j.outcome,
    http_status: j.http_status,
    crm_id: j.crm_id || null,
    verified: Boolean(j.verified),
    service_category: j.category || null,
    qualification_status: (j.values && j.values.x_qualification_status) || null,
    lead_score: j.values ? j.values.x_lead_score : null,
    duration_ms: Date.now() - j.started_ms,
    error: (j.errors || []).join(' | ') || null,
    is_synthetic: true,
  },
}];
