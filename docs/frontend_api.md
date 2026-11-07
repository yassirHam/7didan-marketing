# Frontend ↔ backend API

Owner: Amal (frontend). The FastAPI backend (Amine) implements these three endpoints.
Types are in `frontend/src/lib/contract.ts`.

The browser never calls the backend directly. It calls the Next.js routes `/api/chat`, `/api/enquiries`
and `/api/events`. When `BACKEND_URL` is set, those routes forward the same JSON to
`{BACKEND_URL}/api/chat`, `/api/enquiries` and `/api/events`. When it is empty, the frontend runs in
**demo mode** (see the end of this file).

```
Browser ──▶ Next.js /api/* ──▶ FastAPI /api/* ──▶ backend.crm.CrmClient ──▶ n8n ──▶ Odoo
           (validates shape,     (RAG, scoring,
            timeouts)             funnel events)
```

## POST /api/chat

Request:

```json
{ "conversation_id": "1b7c…-uuid", "message": "Which internet option fits a 20-person office?" }
```

`conversation_id` is a UUID created by the browser for the conversation (8-64 letters, digits or dashes).
`message` is 1-2000 characters.

Response (200):

```json
{
  "answer": "Here is what the catalogue says…\n- Option A: …\n- Option B: …",
  "status": "answered",
  "sources": [
    { "title": "Business catalogue", "section": "Connectivity", "url": "https://…", "retrieved_at": "2026-10-12" }
  ],
  "offer_qualification": true,
  "suggested_service": { "service_interest": "Business fibre", "service_category": "connectivity" }
}
```

| Field | Rule |
|---|---|
| `answer` | Plain text. The UI never renders HTML. Lines starting with `- ` are shown as a list. |
| `status` | `answered`, or `abstained` when the documents do not support an answer. Abstentions get a "Not in the documents" label. |
| `sources` | Shown under the answer. `url` and `retrieved_at` may be `null`. Empty for abstentions. |
| `offer_qualification` | `true` when the visitor shows business interest. The UI then offers "Talk to an advisor about this". The visitor is never forced into the questions. |
| `suggested_service` | Optional. Pre-fills question 1; the visitor can change it. `service_category` is one of `connectivity`, `mobile`, `cloud`, `cybersecurity`, `collaboration`, `other`. |

Errors: any non-200 status. The UI shows "Your message wasn't answered" with a retry button. A JSON
body `{"error": "…"}` is shown to the visitor, so keep it short and safe.

The backend should record `started` (first message of a conversation), `answered` and `abstained`
events itself in `reporting.conversation_events`.

## POST /api/enquiries

Sent once the visitor has answered the three questions, filled in the contact form and ticked consent.

```json
{
  "submission_id": "6f1c2b9e-0d7a-4a43-9c55-0f6d0e9f2a10",
  "conversation_id": "1b7c…-uuid",
  "qualification": {
    "service_interest": "Business fibre", "service_category": "connectivity",
    "need": "Reliable internet for a 20-person office",
    "budget": "About 3,000 MAD per month", "requirements": null, "timeline": "Within 30 days"
  },
  "contact": { "name": "Salma Bennani", "company": "Atlas Logistiq", "email": "salma@example.com", "phone": null },
  "consent": true
}
```

- `submission_id` is generated in the browser when the visitor first presses Send, and **reused on
  every retry** of that enquiry. Pass it unchanged to `Enquiry(submission_id=…)` so the n8n workflow
  can detect duplicates.
- `budget`, `requirements` and `timeline` are `null` when the visitor skipped them. Do not guess them.
- The browser does not send a lead score or a conversation summary. The backend computes
  `lead_score` with its scoring rules and writes `conversation_summary` from the conversation.

Backend steps:

1. Compute `lead_score` and the summary, build `backend.crm.Enquiry`, call `CrmClient.submit()`.
2. Return the `CrmResult` fields as JSON, with `CrmResult.http_status` as the HTTP status:

```json
{ "status": "created", "submission_id": "6f1c…", "crm_id": 42, "verified": true, "retryable": false, "errors": [] }
```

`status` values are the ones in `docs/crm_integration.md`. What the UI does with each:

| status | UI |
|---|---|
| `created` or `duplicate`, with `verified: true` | "Your enquiry has been received" with the reference number. The **only** success state. |
| `created` or `duplicate`, with `verified: false` | "We couldn't verify your enquiry". No success claim. |
| `invalid` | Field messages shown next to the inputs. Messages that start with `contact.<field>` or `qualification.<field>` are matched to that input. |
| `consent_declined` | "Nothing was sent". |
| `crm_unavailable` (or the backend unreachable) | "We couldn't confirm your enquiry yet" + "Try again", same `submission_id`. |
| anything else | "Your enquiry could not be sent", a problem on our side. |

The Next.js route waits up to 100 s for the backend (the client may retry n8n up to 3 times). If the
backend does not answer, it returns `backend_unavailable` with `retryable: true`.

## POST /api/events

```json
{ "conversation_id": "1b7c…-uuid", "event": "qualification_started" }
```

`event` is one of `qualification_started`, `qualification_completed`, `abandoned`. These are the funnel
steps only the browser can see: opening the questions, finishing question 3, and cancelling or closing
the page before finishing. Insert them into `reporting.conversation_events`. Answer 204 with no body.
The UI does not wait for or display the result.

## Demo mode (BACKEND_URL empty)

For building and showing the interface before the backend is ready:

- `/api/chat` answers from a few **illustrative** snippets in `frontend/src/lib/server/demo.ts`, labelled
  "Demo catalogue (illustrative demo data)". Price questions always abstain. A "Demo data" badge is
  shown in the chat header.
- `/api/enquiries` computes a placeholder score (service 0-30, budget 0-40, timeline 0-30, from
  `project_Plan.txt`) and posts directly to the n8n webhook with `WEBHOOK_TOKEN`. The Odoo opportunity
  is real; only the score is a stand-in for the backend's rules.
- `/api/events` accepts events and drops them (no database access from the frontend).
