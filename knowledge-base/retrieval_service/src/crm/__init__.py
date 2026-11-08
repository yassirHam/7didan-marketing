"""CRM integration package for 7didan backend."""

from retrieval_service.src.crm.client import CrmClient, CrmClientError
from retrieval_service.src.crm.scoring import (
    build_conversation_summary,
    compute_lead_score,
)

__all__ = [
    "CrmClient",
    "CrmClientError",
    "build_conversation_summary",
    "compute_lead_score",
]