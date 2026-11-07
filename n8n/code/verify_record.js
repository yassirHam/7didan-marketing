// Success is reported only after the stored opportunity matches what was sent.
const ctx = $('Resolve recheck').isExecuted ? ctxOf('Resolve recheck') : ctxOf('Check create');
const r = $input.first().json;
const failed = rpcFailure(ctx, r);
if (failed) return failed;

const record = (r.result || [])[0];
if (!record) {
  return finish(ctx, 502, 'verification_failed', [`Opportunity ${ctx.crm_id} could not be read back.`]);
}

// many2one fields come back as [id, name]; tag_ids as a list of IDs.
const stored = (key) => (key === 'tag_ids' ? [...record[key]].sort() : Array.isArray(record[key]) ? record[key][0] : record[key]);
const sent = (key) => (key === 'tag_ids' ? [...ctx.values.tag_ids[0][2]].sort() : ctx.values[key]);
const mismatched = READ_FIELDS.filter((key) => JSON.stringify(stored(key)) !== JSON.stringify(sent(key)));
if (mismatched.length) {
  return finish(ctx, 502, 'verification_failed', [`Stored values differ for: ${mismatched.join(', ')}.`]);
}
return finish(ctx, 201, 'created', [], { verified: true });
