"""CRM integration used by the FastAPI backend: send a qualified enquiry to n8n -> Odoo."""
from backend.crm.client import CrmClient, CrmResult
from backend.crm.contract import Contact, Enquiry, Qualification

__all__ = ["Contact", "CrmClient", "CrmResult", "Enquiry", "Qualification"]
