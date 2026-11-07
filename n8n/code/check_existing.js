// A repeated submission returns the existing opportunity instead of creating a second one.
const ctx = ctxOf('Check login');
const r = $input.first().json;
const failed = rpcFailure(ctx, r);
if (failed) return failed;

if (r.result.length) return finish(ctx, 200, 'duplicate', [], { crm_id: r.result[0].id, verified: true });

// Stage, source and tag IDs are looked up by the external IDs created by scripts/configure_odoo.py.
return go(ctx, {
  call: { model: 'ir.model.data', method: 'search_read', args: [[['module', '=', 'x_7didan']]], kwargs: { fields: ['name', 'res_id'] } },
});
