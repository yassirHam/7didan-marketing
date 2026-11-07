"""Fill the dashboard with synthetic demonstration data:  python scripts/seed_demo.py [count]

Enquiries go through the real pipeline (client -> n8n -> Odoo), so the transaction log and
the Odoo records are genuine outcomes. Conversation events stand in for the FastAPI backend,
which writes them in production. Everything is flagged is_synthetic.
"""
from __future__ import annotations

import random
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.crm import Contact, CrmClient, Enquiry, Qualification  # noqa: E402
from scripts.env import load_env, psql  # noqa: E402

SERVICES = [
    ("Business fiber", "connectivity", "Reliable internet for the office"),
    ("Business mobile plans", "mobile", "Mobile lines for the sales team"),
    ("Cloud hosting", "cloud", "Host our ERP outside the office"),
    ("Managed firewall", "cybersecurity", "Protect the company network"),
    ("Video conferencing", "collaboration", "Meetings between two sites"),
]
COMPANIES = ["Atlas Logistiq", "Riad Digital", "Sahara Foods", "Medina Textiles", "Oasis Clinics", "Bahia Studio"]


def synthetic_enquiry(rng: random.Random, conversation_id: str) -> Enquiry:
    service, category, need = rng.choice(SERVICES)
    company = f"{rng.choice(COMPANIES)} {rng.randint(1, 99)} (synthetic)"
    answered = rng.random()
    return Enquiry(
        contact=Contact("Demo Contact", company, f"demo{rng.randint(1000, 9999)}@example.com", "+212 600 000 000"),
        qualification=Qualification(
            service_interest=service, service_category=category, need=need,
            budget=f"About {rng.choice([1, 2, 3, 5, 8])},000 MAD per month" if answered > 0.25 else None,
            requirements="Static IP" if answered > 0.15 else None,
            timeline=rng.choice(["Within 30 days", "This quarter", "Next year"]) if answered > 0.1 else None,
        ),
        lead_score=rng.randint(20, 95), consent=rng.random() > 0.08,
        conversation_summary=f"Synthetic conversation about {service.lower()}.", conversation_id=conversation_id,
    )


def main(count: int) -> None:
    env, rng = load_env(), random.Random(7)
    client = CrmClient(env["N8N_WEBHOOK_URL"], env["WEBHOOK_TOKEN"])
    events: list[tuple[str, str, int]] = []   # (conversation, event, minutes ago)
    outcomes: dict[str, int] = {}
    for _ in range(count):
        conv, t0 = f"demo-{uuid.uuid4().hex[:12]}", rng.randint(60, 20 * 24 * 60)
        steps = iter(range(t0, 0, -1))   # one minute between a conversation's events

        def log(event: str) -> None:
            events.append((conv, event, next(steps)))

        log("started")
        log(rng.choice(["answered", "answered", "abstained"]))
        if rng.random() < 0.3:          # asked a question, never entered qualification
            continue
        log("qualification_started")
        if rng.random() < 0.2:          # left during the three questions
            log("abandoned")
            continue
        log("qualification_completed")
        enquiry = synthetic_enquiry(rng, conv)
        for _ in range(2 if rng.random() < 0.1 else 1):   # some visitors submit twice
            result = client.submit(enquiry)
            outcomes[result.status] = outcomes.get(result.status, 0) + 1
    values = ",\n".join(f"('{conv}', '{event}', now() - interval '{minutes} minutes')" for conv, event, minutes in events)
    psql(env, f"INSERT INTO reporting.conversation_events (conversation_id, event, occurred_at) VALUES\n{values};")
    print(f"{count} synthetic conversations, {len(events)} events; CRM outcomes: {outcomes}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
