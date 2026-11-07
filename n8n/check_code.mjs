// Syntax-check every Code node in the workflow export:  node n8n/check_code.mjs
// Each node body runs inside a function in n8n (top-level return), so it is wrapped the same way.
import { readFileSync } from 'node:fs';

const wf = JSON.parse(readFileSync(new URL('./lead_qualification_workflow.json', import.meta.url), 'utf8'));
let failed = 0;
for (const node of wf.nodes.filter((n) => n.type === 'n8n-nodes-base.code')) {
  try {
    new Function('$', '$input', '$env', node.parameters.jsCode); // compiles only, never runs
    console.log(`ok   ${node.name}`);
  } catch (err) {
    failed += 1;
    console.log(`FAIL ${node.name}: ${err.message}`);
  }
}
process.exit(failed ? 1 : 0);
