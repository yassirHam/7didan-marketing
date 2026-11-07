// Complete the opportunity values with the Odoo IDs for stage, source and service tag.
const ctx = ctxOf('Check existing');
const r = $input.first().json;
const failed = rpcFailure(ctx, r);
if (failed) return failed;

const refs = Object.fromEntries(r.result.map((row) => [row.name, row.res_id]));
const stageKey = ctx.values.x_qualification_status === 'qualified' ? 'stage_qualified' : 'stage_new';
const tagKey = `tag_${ctx.category}`;
const missing = [stageKey, 'source_chatbot', tagKey].filter((key) => !refs[key]);
if (missing.length) {
  return finish(ctx, 500, 'crm_not_configured', [`Missing Odoo references: ${missing.join(', ')}. Run scripts/setup.py.`]);
}

const values = { ...ctx.values, stage_id: refs[stageKey], source_id: refs.source_chatbot, tag_ids: [[6, 0, [refs[tagKey]]]] };
return go(ctx, { values, call: { model: 'crm.lead', method: 'create', args: [values], kwargs: {} } });
