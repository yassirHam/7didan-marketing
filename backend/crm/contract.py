"""The enquiry payload the backend sends to the n8n webhook (see docs/crm_integration.md)."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field

SERVICE_CATEGORIES = ("connectivity", "mobile", "cloud", "cybersecurity", "collaboration", "other")


@dataclass(frozen=True)
class Contact:
    name: str
    company: str
    email: str
    phone: str | None = None


@dataclass(frozen=True)
class Qualification:
    """Answers to the three questions. None means the visitor did not answer (stored as "Unknown")."""
    service_interest: str
    service_category: str
    need: str
    budget: str | None = None
    requirements: str | None = None
    timeline: str | None = None


@dataclass(frozen=True)
class Enquiry:
    contact: Contact
    qualification: Qualification
    lead_score: int
    consent: bool
    conversation_summary: str | None = None
    conversation_id: str | None = None
    # Created once per enquiry and reused on every retry: it is the idempotency key.
    submission_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_payload(self) -> dict:
        return asdict(self)
