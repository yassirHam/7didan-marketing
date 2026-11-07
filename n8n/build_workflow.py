"""Build n8n/lead_qualification_workflow.json from the JavaScript files in n8n/code.

The JSON file is the importable n8n export; the .js files are the source of truth.
Run after editing any Code node:  python n8n/build_workflow.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE / "code"
OUT = HERE / "lead_qualification_workflow.json"
WORKFLOW_ID = "7didanLeadFlow01"
CREDENTIAL = {"postgres": {"id": "7didanReportDB01", "name": "7didan reporting DB (n8n_logger)"}}

PRELUDE = (CODE / "_prelude.js").read_text(encoding="utf-8")
ODOO_URL = "={{ $env.ODOO_URL }}/jsonrpc"
TIMEOUT = {"timeout": "={{ Number($env.ODOO_TIMEOUT_MS) }}"}
LOGIN_BODY = ("={{ JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: { service: 'common', method: 'login', "
              "args: [$env.ODOO_DB, $env.ODOO_INTEGRATION_LOGIN, $env.ODOO_INTEGRATION_PASSWORD] } }) }}")
# Every Odoo model call: the previous Code node puts { model, method, args, kwargs } in $json.call.
# The password is read from the environment here so it never appears in execution data.
CALL_BODY = ("={{ JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: { service: 'object', method: 'execute_kw', "
             "args: [$env.ODOO_DB, $json.uid, $env.ODOO_INTEGRATION_PASSWORD, $json.call.model, $json.call.method, "
             "$json.call.args, $json.call.kwargs || {}] } }) }}")
RESPONSE_BODY = ("={{ JSON.stringify({ status: $json.outcome, submission_id: $json.submission_id, crm_id: $json.crm_id || null, "
                 "verified: Boolean($json.verified), retryable: Boolean($json.retryable), errors: $json.errors || [] }) }}")


def node(name: str, kind: str, version: float, x: int, y: int, parameters: dict, **extra) -> dict:
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"7didan/{name}")), "name": name, "type": f"n8n-nodes-base.{kind}",
            "typeVersion": version, "position": [x, y], "parameters": parameters, **extra}


def code(name: str, file: str, x: int, y: int) -> dict:
    body = (CODE / file).read_text(encoding="utf-8")
    return node(name, "code", 2, x, y, {"jsCode": f"{PRELUDE}\n{body}"})


def odoo_call(name: str, x: int, y: int, body: str = CALL_BODY) -> dict:
    params = {"method": "POST", "url": ODOO_URL, "sendBody": True, "specifyBody": "json", "jsonBody": body, "options": TIMEOUT}
    return node(name, "httpRequest", 4.2, x, y, params, onError="continueRegularOutput")


def branch(name: str, x: int, y: int) -> dict:
    """Output 0 when the previous step says route=continue, output 1 otherwise."""
    return node(name, "switch", 3.2, x, y, {"mode": "expression", "numberOutputs": 2,
                                           "output": "={{ $json.route === 'continue' ? 0 : 1 }}"})


def build() -> dict:
    row1, row2 = 300, 600
    nodes = [
        node("Enquiry webhook", "webhook", 2, 0, row1,
             {"httpMethod": "POST", "path": "7didan/lead", "responseMode": "responseNode", "options": {}},
             webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "7didan/webhook"))),
        code("Validate enquiry", "validate_enquiry.js", 220, row1),
        branch("Valid?", 440, row1),
        odoo_call("Odoo login", 660, row1, LOGIN_BODY),
        code("Check login", "check_login.js", 880, row1),
        branch("Logged in?", 1100, row1),
        odoo_call("Find submission", 1320, row1),
        code("Check existing", "check_existing.js", 1540, row1),
        branch("New submission?", 1760, row1),
        odoo_call("Load references", 1980, row1),
        code("Build opportunity", "build_opportunity.js", 2200, row1),
        branch("References found?", 2420, row1),
        odoo_call("Create opportunity", 2640, row1),
        code("Check create", "check_create.js", 2860, row1),
        branch("Created?", 3080, row1),
        odoo_call("Recheck submission", 3300, row2),
        code("Resolve recheck", "resolve_recheck.js", 3520, row2),
        branch("Recovered?", 3740, row2),
        odoo_call("Read back opportunity", 3960, row1),
        code("Verify record", "verify_record.js", 4180, row1),
        node("Respond", "respondToWebhook", 1.1, 4400, row2 + 300,
             {"respondWith": "json", "responseBody": RESPONSE_BODY, "options": {"responseCode": "={{ $json.http_status }}"}}),
        code("Shape log row", "log_row.js", 4620, row2 + 300),
        node("Log transaction", "postgres", 2.5, 4840, row2 + 300, {
            "schema": {"__rl": True, "mode": "list", "value": "reporting"},
            "table": {"__rl": True, "mode": "list", "value": "crm_transactions"},
            "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
            "options": {},
        }, credentials=CREDENTIAL, onError="continueRegularOutput"),
    ]
    to = lambda *targets: [[{"node": t, "type": "main", "index": 0} for t in targets]]  # noqa: E731
    two = lambda ok, other: [[{"node": ok, "type": "main", "index": 0}], [{"node": other, "type": "main", "index": 0}]]  # noqa: E731
    connections = {
        "Enquiry webhook": {"main": to("Validate enquiry")},
        "Validate enquiry": {"main": to("Valid?")},
        "Valid?": {"main": two("Odoo login", "Respond")},
        "Odoo login": {"main": to("Check login")},
        "Check login": {"main": to("Logged in?")},
        "Logged in?": {"main": two("Find submission", "Respond")},
        "Find submission": {"main": to("Check existing")},
        "Check existing": {"main": to("New submission?")},
        "New submission?": {"main": two("Load references", "Respond")},
        "Load references": {"main": to("Build opportunity")},
        "Build opportunity": {"main": to("References found?")},
        "References found?": {"main": two("Create opportunity", "Respond")},
        "Create opportunity": {"main": to("Check create")},
        "Check create": {"main": to("Created?")},
        "Created?": {"main": two("Read back opportunity", "Recheck submission")},
        "Recheck submission": {"main": to("Resolve recheck")},
        "Resolve recheck": {"main": to("Recovered?")},
        "Recovered?": {"main": two("Read back opportunity", "Respond")},
        "Read back opportunity": {"main": to("Verify record")},
        "Verify record": {"main": to("Respond")},
        "Respond": {"main": to("Shape log row")},
        "Shape log row": {"main": to("Log transaction")},
    }
    return {"id": WORKFLOW_ID, "name": "7didan - enquiry to Odoo opportunity", "active": False, "nodes": nodes,
            "connections": connections, "settings": {"executionOrder": "v1"}, "pinData": {}}


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(HERE.parent)}")
