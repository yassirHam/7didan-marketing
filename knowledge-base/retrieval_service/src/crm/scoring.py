"""Lead scoring and conversation summary for CRM enquiries.

The browser does not send a lead score: the backend computes it from the
qualification answers (see docs/frontend_api.md in the marketing repo).
The score is a priority heuristic, not a conversion probability.

Rules (service 0-30, budget 0-40, timeline 0-30):
- service: 30 for a concrete category, 10 for "other".
- budget: an answered budget gets half of the 40 points (fit cannot be
  judged without published prices), otherwise 0.
- timeline: fixed points per choice, 10 for a custom answer, 0 if skipped.
"""

from retrieval_service.src.api.schemas import Qualification

TIMELINE_POINTS = {
    "As soon as possible": 30,
    "Within 30 days": 25,
    "Within 3 months": 15,
    "Within 6 months": 10,
    "Later, no rush": 5,
}

MAX_SUMMARY_LENGTH = 4000


def compute_lead_score(qualification: Qualification) -> int:
    """Compute the 0-100 lead score from the qualification answers."""
    service = 10 if qualification.service_category == "other" else 30

    budget = 20 if qualification.budget else 0

    if qualification.timeline:
        timeline = TIMELINE_POINTS.get(qualification.timeline, 10)
    else:
        timeline = 0

    return min(100, service + budget + timeline)


def build_conversation_summary(qualification: Qualification) -> str:
    """Build the conversation summary stored in Odoo from the answers."""
    parts = [
        f"Asked about {qualification.service_interest} "
        f"({qualification.service_category}).",
        f"Need: {qualification.need}.",
    ]

    for label, value in (
        ("Budget", qualification.budget),
        ("Requirements", qualification.requirements),
        ("Timeline", qualification.timeline),
    ):
        parts.append(f"{label}: {value if value else 'Not specified'}.")

    return " ".join(parts)[:MAX_SUMMARY_LENGTH]
