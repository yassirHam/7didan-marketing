from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Simple email pattern (avoids the optional email-validator dependency).
EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


class QuestionRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9-]+$"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000
    )


class Source(BaseModel):
    title: str
    section: str | None = None
    url: str | None = None
    retrieved_at: str | None = None


class SuggestedService(BaseModel):
    service_interest: str
    service_category: Literal[
        "connectivity",
        "mobile",
        "cloud",
        "cybersecurity",
        "collaboration",
        "other"
    ]


class AnswerResponse(BaseModel):
    answer: str
    status: Literal["answered", "abstained"]
    sources: list[Source] = Field(default_factory=list)
    offer_qualification: bool = False
    suggested_service: SuggestedService | None = None


# ============================================================
# CRM INTEGRATION MODELS
# ============================================================

class Contact(BaseModel):
    """Contact information for the lead."""
    name: str = Field(..., min_length=1, max_length=120)
    company: str = Field(..., min_length=1, max_length=160)
    email: str = Field(..., pattern=EMAIL_PATTERN)
    phone: str | None = Field(None, pattern=r"^[\d\s+().-]{6,20}$")

    @field_validator("email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        return v.lower()


class Qualification(BaseModel):
    """Lead qualification details."""
    service_interest: str = Field(..., min_length=1)
    service_category: Literal[
        "connectivity",
        "mobile",
        "cloud",
        "cybersecurity",
        "collaboration",
        "other"
    ]
    need: str = Field(..., min_length=1)
    budget: str | None = None
    requirements: str | None = None
    timeline: str | None = None


class Enquiry(BaseModel):
    """Complete enquiry payload for CRM integration."""
    submission_id: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9-]+$"
    )
    contact: Contact
    qualification: Qualification
    lead_score: int = Field(..., ge=0, le=100)
    consent: bool = Field(..., description="Must be true for CRM submission")
    conversation_summary: str | None = Field(None, max_length=4000)
    conversation_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")

    def to_payload(self) -> dict:
        """Convert to JSON-serializable dict for n8n webhook."""
        payload = self.model_dump()
        # Ensure email is lowercase
        payload["contact"]["email"] = payload["contact"]["email"].lower()
        # Convert None values to "Unknown" for optional qualification fields
        for field in ["budget", "requirements", "timeline"]:
            if payload["qualification"][field] is None:
                payload["qualification"][field] = "Unknown"
        return payload


class CrmResponse(BaseModel):
    """Response from n8n webhook after CRM processing."""
    status: Literal[
        "created",
        "duplicate",
        "unauthorized",
        "invalid",
        "consent_declined",
        "crm_auth_failed",
        "crm_error",
        "verification_failed",
        "crm_unavailable",
        "crm_not_configured"
    ]
    submission_id: str
    crm_id: int | None = None
    verified: bool = False
    retryable: bool = False
    errors: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True only for created or duplicate with verified=True."""
        return self.status in ("created", "duplicate") and self.verified

    def get_http_status(self) -> int:
        """Map CRM status to HTTP status code."""
        status_map = {
            "created": 201,
            "duplicate": 200,
            "unauthorized": 401,
            "invalid": 422,
            "consent_declined": 422,
            "crm_auth_failed": 502,
            "crm_error": 502,
            "verification_failed": 502,
            "crm_unavailable": 503,
            "crm_not_configured": 500,
        }
        return status_map.get(self.status, 500)


class CrmSubmitRequest(BaseModel):
    """Request model for submitting a lead to CRM."""
    submission_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    contact_name: str = Field(..., min_length=1, max_length=120)
    contact_company: str = Field(..., min_length=1, max_length=160)
    contact_email: str = Field(..., pattern=EMAIL_PATTERN)
    contact_phone: str | None = Field(None, pattern=r"^[\d\s+().-]{6,20}$")
    service_interest: str = Field(..., min_length=1)
    service_category: Literal[
        "connectivity",
        "mobile",
        "cloud",
        "cybersecurity",
        "collaboration",
        "other"
    ]
    need: str = Field(..., min_length=1)
    budget: str | None = None
    requirements: str | None = None
    timeline: str | None = None
    lead_score: int = Field(..., ge=0, le=100)
    consent: bool
    conversation_summary: str | None = Field(None, max_length=4000)
    conversation_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")

    @field_validator("contact_email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        return v.lower()

    def to_enquiry(self) -> Enquiry:
        """Convert to Enquiry model."""
        return Enquiry(
            submission_id=self.submission_id,
            contact=Contact(
                name=self.contact_name,
                company=self.contact_company,
                email=self.contact_email,
                phone=self.contact_phone,
            ),
            qualification=Qualification(
                service_interest=self.service_interest,
                service_category=self.service_category,
                need=self.need,
                budget=self.budget,
                requirements=self.requirements,
                timeline=self.timeline,
            ),
            lead_score=self.lead_score,
            consent=self.consent,
            conversation_summary=self.conversation_summary,
            conversation_id=self.conversation_id,
        )


# ============================================================
# FRONTEND CONTRACT MODELS (docs/frontend_api.md)
# ============================================================

class EnquiryRequest(BaseModel):
    """POST /api/enquiries body, exactly as the frontend sends it.

    The browser does NOT send lead_score or conversation_summary:
    the backend computes them (see crm/scoring.py).
    """
    submission_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    conversation_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    qualification: Qualification
    contact: Contact
    consent: bool

    def to_enquiry(self, lead_score: int, conversation_summary: str | None) -> Enquiry:
        """Convert to the Enquiry payload sent to the n8n webhook."""
        return Enquiry(
            submission_id=self.submission_id,
            contact=self.contact,
            qualification=self.qualification,
            lead_score=lead_score,
            consent=self.consent,
            conversation_summary=conversation_summary,
            conversation_id=self.conversation_id,
        )


class EventRequest(BaseModel):
    """POST /api/events body (funnel steps only the browser can see)."""
    conversation_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    event: Literal[
        "qualification_started",
        "qualification_completed",
        "abandoned",
    ]