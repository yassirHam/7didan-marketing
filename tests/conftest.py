"""Fixtures for the end-to-end tests (backend client -> n8n -> Odoo) and the test report.

The stack must be running (python scripts/setup.py). Each test's docstring is
"<scenario>\n\nExpected: <expected result>"; tests add the observed result with
record_property("observed", ...). The session writes docs/integration_test_report.md.
"""
from __future__ import annotations

import inspect
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.crm import Contact, CrmClient, Enquiry, Qualification
from scripts.env import ROOT, load_env, psql
from scripts.odoo_rpc import Odoo

ODOO_URL = "http://localhost:8069"
RESULTS: list[dict] = []


@pytest.fixture(scope="session")
def env() -> dict[str, str]:
    return load_env()


@pytest.fixture(scope="session")
def odoo(env) -> Odoo:
    return Odoo(ODOO_URL, env["ODOO_DB"], env["ODOO_ADMIN_LOGIN"], env["ODOO_ADMIN_PASSWORD"])


@pytest.fixture(scope="session")
def crm(env) -> CrmClient:
    """Single attempt, so each test observes exactly one workflow run."""
    return CrmClient(env["N8N_WEBHOOK_URL"], env["WEBHOOK_TOKEN"], timeout=60, max_attempts=1)


def make_enquiry(**overrides) -> Enquiry:
    """A valid synthetic enquiry; keyword arguments replace top-level or qualification fields."""
    q_fields = {"service_interest": "Business fiber", "service_category": "connectivity",
                "need": "Reliable internet for a 20-person office", "budget": "About 3,000 MAD per month",
                "requirements": "Static IP, backup link", "timeline": "Within 30 days"}
    q_fields.update({k: overrides.pop(k) for k in list(overrides) if k in q_fields})
    values = {"contact": Contact("Salma Bennani", "Atlas Logistiq (synthetic)", "Salma.Demo@example.com", "+212 600 000 000"),
              "qualification": Qualification(**q_fields), "lead_score": 82, "consent": True,
              "conversation_summary": "Asked which offer fits a 20-person office; answered from the catalogue.",
              "conversation_id": f"conv-{uuid.uuid4().hex[:12]}"}
    values.update(overrides)
    return Enquiry(**values)


def raw_post(env: dict[str, str], payload: dict, token: str | None) -> tuple[int, dict]:
    """POST without the client, to send malformed payloads or wrong tokens."""
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-7didan-Token"] = token
    req = urllib.request.Request(env["N8N_WEBHOOK_URL"], json.dumps(payload).encode(), headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def records_for(odoo: Odoo, submission_id: str, fields: tuple[str, ...] = ("id",)) -> list[dict]:
    return odoo.search_read("crm.lead", [("x_submission_id", "=", submission_id)], list(fields),
                            context={"active_test": False})


def logged_outcomes(env: dict[str, str], submission_id: str, expected: int = 1, timeout: float = 10) -> list[str]:
    """Outcomes logged by n8n for a submission. Logging runs after the response, so poll briefly."""
    deadline = time.monotonic() + timeout
    while True:
        out = psql(env, "SELECT outcome FROM reporting.crm_transactions WHERE submission_id = :'sid' ORDER BY id;",
                   variables={"sid": submission_id})
        rows = out.splitlines() if out else []
        if len(rows) >= expected or time.monotonic() > deadline:
            return rows
        time.sleep(0.5)


# ── test report ─────────────────────────────────────────────────────────────
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    report = (yield).get_result()
    if report.when == "call" or (report.when == "setup" and not report.passed):
        doc = inspect.getdoc(getattr(item, "function", None)) or item.name
        scenario, _, expected = doc.partition("Expected:")
        props = dict(report.user_properties)
        RESULTS.append({
            "test": item.name, "scenario": " ".join(scenario.split()), "expected": " ".join(expected.split()),
            "observed": props.get("observed", "" if report.passed else str(report.longrepr).splitlines()[-1]),
            "result": "PASS" if report.passed else ("SKIP" if report.skipped else "FAIL"),
            "seconds": round(report.duration, 2),
        })


def pytest_sessionfinish(session, exitstatus):
    if not RESULTS:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out_dir = ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integration_results.json").write_text(json.dumps({"run_at": stamp, "results": RESULTS}, indent=2), encoding="utf-8")
    passed = sum(r["result"] == "PASS" for r in RESULTS)
    lines = [
        "# Integration test report: backend -> n8n -> Odoo CRM", "",
        f"Run: {stamp}. Result: {passed}/{len(RESULTS)} passed. All enquiries are synthetic.", "",
        "Generated by `python -m pytest` from tests/test_crm_workflow.py. Do not edit by hand.", "",
        "| # | Scenario | Expected | Observed | Result |", "|---|---|---|---|---|",
    ]
    cell = lambda s: str(s).replace("|", "\\|")  # noqa: E731
    for i, r in enumerate(RESULTS, 1):
        lines.append(f"| {i} | {cell(r['scenario'])} | {cell(r['expected'])} | {cell(r['observed'])} | {r['result']} |")
    lines += ["", "Limitations of these tests are listed in docs/crm_integration.md."]
    Path(ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "integration_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
