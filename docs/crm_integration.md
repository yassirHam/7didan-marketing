# CRM integration: FastAPI → n8n → Odoo

Owner: Yassir. Support: Amine (backend side of the contract).

## Flow

```
FastAPI backend ──POST /webhook/7didan/lead──▶ n8n workflow ──JSON-RPC──▶ Odoo CRM
  (backend/crm/client.py)   X-7didan-Token      (n8n/code/*.js)          integration user
        ▲                                             │
        └──────── status, crm_id, verified ───────────┤
                                                      └──▶ reporting.crm_transactions (PostgreSQL)
```

Workflow steps (`n8n/lead_qualification_workflow.json`):

1. **Validate enquiry**: checks the token, every field and consent, then maps the payload to Odoo fields. Invalid data stops here.
2. **Odoo login** with the restricted integration account.
3. **Find submission**: looks for an opportunity that already has this `submission_id` (idempotency).
4. **Load references**: stage, source and tag IDs from the external IDs created by `scripts/configure_odoo.py`.
5. **Create opportunity**. If the call fails or times out, **Recheck submission** looks the ID up again before anything is retried.
6. **Read back opportunity** and **Verify record**: success is reported only if the stored values match what was sent.
7. **Respond**, then **Log transaction** into `reporting.crm_transactions`.

## Request

`POST {N8N_WEBHOOK_URL}` with header `X-7didan-Token: {WEBHOOK_TOKEN}`. Built by `backend.crm.Enquiry.to_payload()`.

```json
{
  "submission_id": "6f1c2b9e-0d7a-4a43-9c55-0f6d0e9f2a10",
  "contact": {"name": "Salma Bennani", "company": "Atlas Logistiq", "email": "salma@example.com", "phone": "+212 600 000 000"},
  "qualification": {
    "service_interest": "Business fiber", "service_category": "connectivity",
    "need": "Reliable internet for a 20-person office",
    "budget": "About 3,000 MAD per month", "requirements": "Static IP", "timeline": "Within 30 days"
  },
  "lead_score": 82,
  "consent": true,
  "conversation_summary": "Asked which offer fits a 20-person office.",
  "conversation_id": "conv-1234"
}
```

| Field | Rule |
|---|---|
| `submission_id` | Required, 8-64 letters, digits or dashes. Generate once per enquiry and reuse it on every retry. |
| `contact.name`, `contact.company` | Required, max 120 / 160 characters. |
| `contact.email` | Required, valid address. Stored lowercase. |
| `contact.phone` | Optional, 6-20 digits, spaces, `+ ( ) . -`. |
| `qualification.service_interest`, `need` | Required (questions 1). |
| `qualification.service_category` | `connectivity`, `mobile`, `cloud`, `cybersecurity`, `collaboration` or `other`. |
| `qualification.budget`, `requirements`, `timeline` | Optional (questions 2 and 3). `null` is stored as `Unknown`. |
| `lead_score` | Required integer 0-100, computed by the backend's scoring rules. |
| `consent` | Must be `true`, otherwise nothing is sent to Odoo. |
| `conversation_summary` | Optional, max 4000 characters. Stored as escaped text. |

## Response

```json
{"status": "created", "submission_id": "6f1c…", "crm_id": 42, "verified": true, "retryable": false, "errors": []}
```

| HTTP | `status` | Meaning | Backend action |
|---|---|---|---|
| 201 | `created` | Opportunity created and read back. | Confirm to the visitor. |
| 200 | `duplicate` | This `submission_id` is already in Odoo; `crm_id` is that record. | Confirm (it is the same enquiry). |
| 401 | `unauthorized` | Missing or wrong `X-7didan-Token`. | Fix configuration. Do not retry. |
| 422 | `invalid` | Validation failed; `errors` lists every problem. | Ask the visitor to correct. |
| 422 | `consent_declined` | `consent` is not `true`. | Nothing was sent to the CRM. |
| 502 | `crm_auth_failed` | Odoo rejected the integration credentials. | Alert; do not retry. |
| 502 | `crm_error` | Odoo refused the record (for example a validation error). | Alert; do not retry. |
| 502 | `verification_failed` | The stored record differs from what was sent. | Alert; do not confirm. |
| 503 | `crm_unavailable` | Odoo unreachable or timed out, and no record exists. `retryable: true`. | Retry with the same `submission_id`. |
| 500 | `crm_not_configured` | Stage, source or tag references are missing. | Run `python scripts/setup.py`. |

`CrmResult.ok` is true only for `created` or `duplicate` with `verified: true`. The interface must not show success otherwise.

## Field mapping (Odoo `crm.lead`, type `opportunity`)

| Payload | Odoo field |
|---|---|
| `contact.company` + `service_interest` | `name` ("Atlas Logistiq - Business fiber") |
| `contact.company` / `name` / `email` / `phone` | `partner_name` / `contact_name` / `email_from` / `phone` |
| `conversation_summary` | `description` (HTML-escaped) |
| `service_interest`, `need`, `budget`, `requirements`, `timeline` | `x_service_interest`, `x_need`, `x_budget`, `x_requirements`, `x_timeline` |
| `lead_score` | `x_lead_score` |
| derived (below) | `x_qualification_status`, `stage_id` |
| `service_category` | `tag_ids` (Connectivity, Mobile, Cloud, Cybersecurity, Collaboration, Other) |
| constant | `source_id` = "7didan chatbot", `x_consent` = true |
| `submission_id`, `conversation_id` | `x_submission_id` (unique), `x_conversation_id` |

Qualification status: `partial` if budget, requirements or timeline is unknown; otherwise `qualified` when
`lead_score` ≥ 60, else `not_qualified`. Qualified opportunities start in stage **Qualified**, the others in **New**.
The score is a priority heuristic, not a conversion probability, and does not describe Orange Maroc's rules.

## Idempotency and failure handling

- **Repeated requests**: step 3 finds the existing record and returns `duplicate`.
- **Concurrent identical requests**: a unique index on `crm_lead.x_submission_id` lets only one create succeed;
  the other gets a unique-violation error, rechecks, and returns `duplicate`.
- **Timeout after Odoo committed**: the recheck finds the record, verifies it and returns `created`.
  The backend retry (same `submission_id`) is also safe because every run starts with step 3.
- **Odoo down**: `crm_unavailable` with `retryable: true` and no record. `CrmClient` retries up to 3 times with backoff.
- **Invalid data, missing consent, wrong token**: rejected before any Odoo call.

## Security

- Odoo is called with `n8n-integration`, an internal user with Sales "All Documents" rights plus one
  custom group, "7didan integration: external IDs". That group can read `ir.model.data` rows of module
  `x_7didan` only (an access right plus a record rule), which is how the workflow resolves stage, source
  and tag IDs without the Administration/Access Rights group.
- Secrets live in `.env` (not committed) and reach n8n as environment variables. The Odoo password is
  injected into the HTTP body by expression, so it never appears in n8n execution data.
- `n8n_logger` can only insert into and read `reporting.crm_transactions`; `powerbi_reader` can only read the `reporting` schema.
- All ports are bound to `127.0.0.1`. The chat summary is untrusted input and is stored escaped.

## Limitations

- Tested against a local Odoo 18 Community instance with synthetic data only; no load or soak testing.
- The webhook token is a shared secret compared in plain JavaScript (no request signing or rate limiting).
- n8n's own failure (crash between create and respond) is covered only by the backend retry plus the recheck.
- Field verification covers the structured fields; `description` is not compared because Odoo sanitises HTML.
- The dashboard measures a simulated workflow; it says nothing about real Orange Maroc sales or conversion.
