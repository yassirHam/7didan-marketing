# 7didan frontend

Amal's part of the Group 10 project: the website, the chatbot interface, the three-question
qualification, the contact and consent form, and the connection to the FastAPI backend.
Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4.

Independent academic prototype. Not affiliated with or endorsed by Orange Maroc.

## Pages

| URL | What it is |
|---|---|
| `/` | Landing page: what the assistant does, how it works, service topics that open the chat with a starter question. |
| `/chat` | The assistant. `/chat?q=…` pre-fills the first question. |

## The journey on `/chat`

1. **Ask.** The visitor asks in their own words. Answers show their sources. When the documents don't
   cover a question the answer is labelled "Not in the documents" and nothing is guessed.
2. **Offer.** When an answer shows business interest, a "Talk to an advisor about this" button appears.
   The header button opens the questions at any time. Nobody is pushed into the sales flow.
3. **Three questions**, one per card, with a progress bar:
   - Which service, and what should it achieve (service area, service, need: required).
   - Approximate budget and essential requirements (each can be left as "don't know").
   - Timeline (choices, own words, or "not decided").
   Skipped answers are sent as `null` and stored in Odoo as "Unknown".
4. **Contact and consent.** A summary of the answers (editable), name, company, email, optional phone,
   and a consent checkbox. Without consent nothing is sent; "No thanks, don't contact me" ends the flow.
5. **Result.** Success is shown only when the record was created **and verified** in Odoo. Otherwise
   the visitor sees what to do: fix fields, try again (safe, same submission ID), or that it failed.

Funnel events (`qualification_started`, `qualification_completed`, `abandoned`) are sent for the dashboard.

## Run

From `7didan/`, with the CRM stack already set up (`python scripts/setup.py`):

```powershell
docker compose up -d --build frontend     # http://localhost:3000
```

For development with hot reload:

```powershell
cd frontend
Copy-Item .env.example .env.local         # set WEBHOOK_TOKEN to the value in ../.env
npm install
npm run dev                               # http://localhost:3000
```

Checks:

```powershell
npm run lint
npm run build
```

## Configuration (server-side only)

| Variable | Use |
|---|---|
| `BACKEND_URL` | FastAPI backend base URL. When set, `/api/*` forwards to it. Empty = demo mode. |
| `N8N_WEBHOOK_URL`, `WEBHOOK_TOKEN` | Demo mode only: enquiries go straight to Yassir's n8n webhook, so they create real Odoo opportunities. |

None of these reach the browser: there are no `NEXT_PUBLIC_` variables. The webhook token stays on the server.

## Demo mode

Without a backend the chat answers from a few illustrative snippets (a "Demo data" badge is shown and
each answer says it is demo data), price questions always abstain, and the lead score is a placeholder.
Details and the API the backend must implement: `../docs/frontend_api.md`.

## Code layout

```
src/app/page.tsx                 landing page
src/app/chat/page.tsx            assistant page
src/app/api/chat|enquiries|events/route.ts
                                 server routes: check the request shape, forward or answer in demo mode
src/components/chat/             ChatApp, MessageBubble, Composer, Qualification (3 steps), ContactStep, ResultCard
src/components/ui.tsx            buttons, fields, alerts, logo
src/hooks/useConversation.ts     conversation state: chat → 3 questions → contact → result
src/lib/contract.ts              API types shared with the backend
src/lib/validation.ts            field rules (same limits as the n8n workflow)
src/lib/outcome.ts               what the visitor sees for each enquiry status
src/lib/client.ts                browser fetch calls with timeouts
src/lib/server/                  forwarding to the backend, demo backend
```

## Accessibility and responsiveness

- Works from 360 px phones to desktop; the questions appear as a panel under the conversation.
- Keyboard: Enter sends, Shift+Enter adds a line. Each new step moves focus to its heading.
- Labels on every input, errors linked with `aria-describedby`, the conversation is a polite live region.
- Animations are turned off when the system asks for reduced motion.
