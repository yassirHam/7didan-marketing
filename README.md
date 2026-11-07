# 7didan: CRM, automation, analytics and frontend

Group 10 project. Yassir's part: Odoo CRM configuration, the n8n workflow, the CRM integration used
by the FastAPI backend, the Power BI data model, and the integration tests. Amal's part: the Next.js
website and chatbot in `frontend/` (see `frontend/README.md`).
Independent academic prototype using synthetic data. Not affiliated with or endorsed by Orange Maroc.

| Deliverable | Where |
|---|---|
| Website, chatbot, qualification screens | `frontend/`, API contract in `docs/frontend_api.md` |
| Odoo CRM configuration | `scripts/configure_odoo.py`, `odoo/crm_lead_form.xml` |
| n8n workflow export | `n8n/lead_qualification_workflow.json` (built from `n8n/code/*.js`) |
| CRM integration | `backend/crm/` (client for FastAPI), `docs/crm_integration.md` (contract) |
| Power BI dashboard | `database/reporting_views.sql`, `powerbi/` (measures, theme, build steps) |
| Integration test report | `tests/test_crm_workflow.py` → `docs/integration_test_report.md` |

## Requirements

Docker Desktop, Python 3.11+ with `pytest`, and Power BI Desktop for the dashboard.

## Run

```powershell
Copy-Item .env.example .env        # then replace every value
python scripts/setup.py            # starts PostgreSQL, Odoo 18, n8n 1.88 and configures everything
python -m pytest                   # end-to-end tests, writes docs/integration_test_report.md
python scripts/seed_demo.py 40     # optional: synthetic data for the dashboard
docker compose up -d --build frontend   # website and chatbot on http://localhost:3000
```

- Website: http://localhost:3000. Without `BACKEND_URL` it runs in demo mode (illustrative answers,
  enquiries sent straight to n8n, so they still create verified Odoo opportunities).
- Odoo: http://localhost:8069 (admin login from `.env`). Opportunities show a **7didan qualification** tab.
- n8n: http://localhost:5678. The workflow is imported and activated on every container start.
- Webhook: `POST http://localhost:5678/webhook/7didan/lead`.

## Using it from the FastAPI backend

```python
from backend.crm import Contact, CrmClient, Enquiry, Qualification

crm = CrmClient(settings.n8n_webhook_url, settings.webhook_token)
result = crm.submit(Enquiry(
    contact=Contact("Salma Bennani", "Atlas Logistiq", "salma@example.com"),
    qualification=Qualification("Business fiber", "connectivity", "Internet for 20 people",
                                budget="About 3,000 MAD per month", requirements=None, timeline="Within 30 days"),
    lead_score=82, consent=True, conversation_summary=summary, conversation_id=conversation_id,
))
if result.ok:        # created or duplicate, and verified in Odoo
    ...
```

Create the `Enquiry` once and reuse it when retrying: its `submission_id` is the idempotency key.
The backend also writes funnel events to `reporting.conversation_events` (see `database/reporting.sql`).

## Changing the workflow

Edit the JavaScript in `n8n/code/`, then run `python n8n/build_workflow.py` and
`docker compose restart n8n`. Do not edit the JSON export by hand.

## Layout

```
backend/crm/      client and payload contract for the FastAPI backend
database/         reporting schema, views, idempotency index, database roles
docs/             integration contract, frontend API contract, generated test report
frontend/         Next.js website and chatbot (Amal)
n8n/              workflow sources (code/), builder, export, container entrypoint
odoo/             opportunity form extension
powerbi/          DAX measures, theme, dashboard build and validation steps
scripts/          setup, Odoo configuration, demo data
tests/            end-to-end tests
```
