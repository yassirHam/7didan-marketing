"""Configure Odoo CRM for 7didan. Safe to run repeatedly: every step is get-or-create.

Creates the custom qualification fields, the qualification form tab, lead sources,
service tags, the restricted n8n integration user, and external IDs (module x_7didan)
that the n8n workflow uses to resolve stage, source and tag IDs.
"""
from __future__ import annotations

from pathlib import Path

from scripts.odoo_rpc import Odoo

MODULE = "x_7didan"
FORM_VIEW = Path(__file__).resolve().parent.parent / "odoo" / "crm_lead_form.xml"

# (name, label, type, extra attributes)
FIELDS = [
    ("x_submission_id", "Submission ID", "char", {"index": True, "copied": False}),
    ("x_conversation_id", "Conversation ID", "char", {"copied": False}),
    ("x_service_interest", "Service interest", "char", {}),
    ("x_need", "Need", "text", {}),
    ("x_budget", "Budget", "char", {}),
    ("x_requirements", "Requirements", "text", {}),
    ("x_timeline", "Timeline", "char", {}),
    ("x_lead_score", "Lead score (0-100)", "integer", {}),
    ("x_qualification_status", "Qualification status", "selection", {"selection_ids": [
        (0, 0, {"value": "qualified", "name": "Qualified", "sequence": 1}),
        (0, 0, {"value": "partial", "name": "Partially qualified", "sequence": 2}),
        (0, 0, {"value": "not_qualified", "name": "Not qualified", "sequence": 3}),
    ]}),
    ("x_consent", "Contact consent", "boolean", {}),
]
SOURCES = {"source_chatbot": "7didan chatbot", "source_manual": "Manual form (baseline)"}
TAGS = {f"tag_{key}": label for key, label in [
    ("connectivity", "Connectivity"), ("mobile", "Mobile"), ("cloud", "Cloud"),
    ("cybersecurity", "Cybersecurity"), ("collaboration", "Collaboration"), ("other", "Other"),
]}
# Odoo's default pipeline stages (crm module data): New, Qualified, Proposition, Won.
STAGES = {"stage_new": "crm.stage_lead1", "stage_qualified": "crm.stage_lead2",
          "stage_proposal": "crm.stage_lead3", "stage_won": "crm.stage_lead4"}
INTEGRATION_GROUPS = ["base.group_user", "sales_team.group_sale_salesman_all_leads"]
REFS_GROUP = "7didan integration: external IDs"


def set_xmlid(odoo: Odoo, name: str, model: str, res_id: int) -> None:
    rows = odoo.search_read("ir.model.data", [("module", "=", MODULE), ("name", "=", name)], ["res_id"])
    if rows:
        if rows[0]["res_id"] != res_id:
            odoo.call("ir.model.data", "write", [rows[0]["id"]], {"res_id": res_id, "model": model})
    else:
        odoo.call("ir.model.data", "create", {"module": MODULE, "name": name, "model": model,
                                               "res_id": res_id, "noupdate": True})


def get_or_create(odoo: Odoo, model: str, domain: list, values: dict) -> int:
    ids = odoo.call(model, "search", domain, limit=1)
    return ids[0] if ids else odoo.call(model, "create", values)


def ensure_fields(odoo: Odoo) -> None:
    model_id = odoo.call("ir.model", "search", [("model", "=", "crm.lead")])[0]
    existing = {f["name"] for f in odoo.search_read(
        "ir.model.fields", [("model", "=", "crm.lead"), ("name", "in", [f[0] for f in FIELDS])], ["name"])}
    for name, label, ttype, extra in FIELDS:
        if name not in existing:
            odoo.call("ir.model.fields", "create", {"name": name, "field_description": label, "model_id": model_id,
                                                    "ttype": ttype, "state": "manual", **extra})
            print(f"  field {name} created")


def ensure_form_tab(odoo: Odoo) -> None:
    arch = FORM_VIEW.read_text(encoding="utf-8")
    values = {"name": "crm.lead.form.7didan", "model": "crm.lead", "type": "form",
              "inherit_id": odoo.ref("crm.crm_lead_view_form"), "arch_base": arch, "priority": 99}
    ids = odoo.call("ir.ui.view", "search", [("name", "=", values["name"])])
    if ids:
        odoo.call("ir.ui.view", "write", ids, {"arch_base": arch})
    else:
        odoo.call("ir.ui.view", "create", values)


def ensure_references(odoo: Odoo) -> None:
    for key, name in SOURCES.items():
        set_xmlid(odoo, key, "utm.source", get_or_create(odoo, "utm.source", [("name", "=", name)], {"name": name}))
    for key, name in TAGS.items():
        set_xmlid(odoo, key, "crm.tag", get_or_create(odoo, "crm.tag", [("name", "=", name)], {"name": name}))
    for key, xmlid in STAGES.items():
        set_xmlid(odoo, key, "crm.stage", odoo.ref(xmlid))


def ensure_reference_access(odoo: Odoo) -> int:
    """Group allowed to read this project's external IDs (module x_7didan) and no other ir.model.data rows.

    Odoo restricts ir.model.data to the Access Rights admin group; n8n only needs to resolve its own references.
    """
    group = get_or_create(odoo, "res.groups", [("name", "=", REFS_GROUP)], {"name": REFS_GROUP})
    model_id = odoo.call("ir.model", "search", [("model", "=", "ir.model.data")])[0]
    access = {"name": "7didan: read own external IDs", "model_id": model_id, "group_id": group,
              "perm_read": True, "perm_write": False, "perm_create": False, "perm_unlink": False}
    ids = odoo.call("ir.model.access", "search", [("name", "=", access["name"])])
    if ids:
        odoo.call("ir.model.access", "write", ids, access)
    else:
        odoo.call("ir.model.access", "create", access)
    rule = {"name": "7didan: own external IDs only", "model_id": model_id, "groups": [(6, 0, [group])],
            "domain_force": f"[('module', '=', '{MODULE}')]",
            "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": True}
    ids = odoo.call("ir.rule", "search", [("name", "=", rule["name"])])
    if ids:
        odoo.call("ir.rule", "write", ids, rule)
    else:
        odoo.call("ir.rule", "create", rule)
    return group


def ensure_integration_user(odoo: Odoo, login: str, password: str) -> int:
    """Internal user with Sales 'All Documents' rights and read access to the project's external IDs only:
    no settings, no accounting, no admin."""
    groups = [odoo.ref(x) for x in INTEGRATION_GROUPS] + [ensure_reference_access(odoo)]
    values = {"name": "n8n integration", "login": login, "password": password, "groups_id": [(6, 0, groups)]}
    ids = odoo.call("res.users", "search", [("login", "=", login)], context={"active_test": False})
    if ids:
        odoo.call("res.users", "write", ids, {**values, "active": True})
        return ids[0]
    return odoo.call("res.users", "create", values)


def configure(odoo: Odoo, integration_login: str, integration_password: str) -> None:
    print("Configuring Odoo CRM")
    ensure_fields(odoo)
    ensure_form_tab(odoo)
    ensure_references(odoo)
    uid = ensure_integration_user(odoo, integration_login, integration_password)
    print(f"  integration user {integration_login!r} (id {uid}) ready")
