
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse

from retrieval_service.src.chains.rag_chain import guarded_rag_chain
from retrieval_service.src.api.schemas import (
    AnswerResponse,
    QuestionRequest,
    Source,
    CrmSubmitRequest,
    CrmResponse,
    EnquiryRequest,
    EventRequest,
)
from retrieval_service.src.crm.client import CrmClient, CrmClientError, create_crm_client
from retrieval_service.src.crm.scoring import (
    build_conversation_summary,
    compute_lead_score,
)
from retrieval_service.src.crm.events import (
    get_event_store,
    record_safe,
    conversation_started,
)


logger = logging.getLogger(__name__)

# Global CRM client instance
_crm_client: Optional[CrmClient] = None


def get_crm_client() -> Optional[CrmClient]:
    """Get or create the CRM client."""
    global _crm_client
    if _crm_client is None:
        try:
            _crm_client = create_crm_client()
        except CrmClientError as e:
            logger.warning("CRM client not configured: %s", e)
            return None
    return _crm_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting 7didan API")
    yield
    # Shutdown
    global _crm_client
    if _crm_client:
        _crm_client.close()
        _crm_client = None
    try:
        get_event_store().close()
    except Exception:
        logger.exception("Error closing event store")
    logger.info("Shutting down 7didan API")


app = FastAPI(
    title="7didan: Orange Maroc Business AI Assistant",
    description="RAG API for Orange Maroc Business products and services with CRM integration.",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/api")
def root():
    return {
        "message": "7didan API",
        "status": "running"
    }


@app.get("/api/health")
def health_check():
    crm_configured = get_crm_client() is not None
    return {
        "status": "healthy",
        "crm_configured": crm_configured
    }


def extract_sources(documents: list) -> list[Source]:
    """Convert retrieved documents into frontend source objects."""

    sources = []
    seen = set()

    for document in documents:
        metadata = document.metadata

        title = (
            metadata.get("title")
            or metadata.get("source")
            or "Orange Maroc Business documentation"
        )

        section = (
            metadata.get("section_h3")
            or metadata.get("section_h2")
            or metadata.get("section_h1")
        )

        # The URL is stored in the vector metadata by the ingestion pipeline
        # (sidecar .json -> cleaner -> chunker -> indexer). Fall back to
        # "source_url" for rows indexed by an older pipeline version.
        url = metadata.get("url") or metadata.get("source_url")

        key = (title, section)

        if key in seen:
            continue

        seen.add(key)

        sources.append(
            Source(
                title=title,
                section=section,
                url=url,
                retrieved_at=None
            )
        )

    return sources


@app.post("/api/chat", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):

    message = request.message.strip()

    if not message:
        return JSONResponse(
            status_code=400,
            content={"error": "Message cannot be empty."}
        )

    # Funnel events (reporting.conversation_events). Never let logging
    # failures break the chat response.
    if conversation_started(request.conversation_id):
        record_safe(request.conversation_id, "started")

    try:
        result = guarded_rag_chain(message)

        status = result["status"]

        record_safe(request.conversation_id, status)

        sources = (
            extract_sources(result.get("documents", []))
            if status == "answered"
            else []
        )

        return AnswerResponse(
            answer=result["answer"],
            status=status,
            sources=sources,

            # Use the conversation-intelligence results.
            offer_qualification=result.get(
                "offer_qualification", False
            ),

            suggested_service=result.get(
                "suggested_service"
            )
        )

    except Exception:
        logger.exception("Error while processing chat request")

        return JSONResponse(
            status_code=500,
            content={
                "error": "An error occurred while processing your message."
            }
        )


# ============================================================
# CRM INTEGRATION ENDPOINTS
# ============================================================

def _submit_enquiry(enquiry) -> JSONResponse:
    """Shared CRM submission logic: send the Enquiry via n8n webhook."""
    crm_client = get_crm_client()
    if crm_client is None:
        logger.error("CRM client not configured - missing N8N_WEBHOOK_URL or WEBHOOK_TOKEN")
        return JSONResponse(
            status_code=500,
            content=CrmResponse(
                status="crm_not_configured",
                submission_id=enquiry.submission_id,
                verified=False,
                retryable=False,
                errors=["CRM integration not configured. Set N8N_WEBHOOK_URL and WEBHOOK_TOKEN."]
            ).model_dump()
        )

    logger.info("Submitting enquiry to CRM: submission_id=%s", enquiry.submission_id)

    try:
        crm_response = crm_client.submit_enquiry(enquiry)
    except CrmClientError as e:
        logger.exception("CRM client error for submission %s", enquiry.submission_id)
        return JSONResponse(
            status_code=e.status_code,
            content=CrmResponse(
                status="crm_error",
                submission_id=enquiry.submission_id,
                verified=False,
                retryable=e.retryable,
                errors=[str(e)]
            ).model_dump()
        )
    except Exception as e:
        logger.exception("Unexpected error submitting to CRM for submission %s", enquiry.submission_id)
        return JSONResponse(
            status_code=500,
            content=CrmResponse(
                status="crm_error",
                submission_id=enquiry.submission_id,
                verified=False,
                retryable=False,
                errors=[f"Internal error: {str(e)}"]
            ).model_dump()
        )

    # Return response with the HTTP status mapped from the CRM status.
    http_status = crm_response.get_http_status()
    return JSONResponse(
        status_code=http_status,
        content=crm_response.model_dump()
    )


@app.post("/api/enquiries")
def submit_enquiry(request: EnquiryRequest):
    """POST /api/enquiries — frontend contract (docs/frontend_api.md).

    The browser sends submission_id, conversation_id, qualification,
    contact and consent. The backend computes lead_score and the
    conversation summary, builds the Enquiry and submits it to CRM via
    the n8n webhook. The response body is the CrmResult fields and the
    HTTP status is mapped from the CRM status (201 created, 200
    duplicate, 401/422/502/503/500 for the failure cases).
    """
    lead_score = compute_lead_score(request.qualification)
    summary = build_conversation_summary(request.qualification)

    enquiry = request.to_enquiry(
        lead_score=lead_score,
        conversation_summary=summary,
    )

    return _submit_enquiry(enquiry)


@app.post("/api/crm/submit", response_model=CrmResponse)
def submit_to_crm(request: CrmSubmitRequest):
    """Submit a qualified lead to CRM via n8n webhook (flat request shape).

    Kept for backward compatibility; the frontend uses /api/enquiries.
    """
    return _submit_enquiry(request.to_enquiry())


@app.post("/api/events", status_code=204, response_class=Response)
def record_funnel_event(request: EventRequest):
    """POST /api/events — record browser-only funnel events.

    Inserts into reporting.conversation_events and answers 204 with no
    body. The UI does not wait for or display the result, so logging
    failures are swallowed after being logged.
    """
    record_safe(request.conversation_id, request.event)
    return Response(status_code=204)


@app.get("/api/crm/status/{submission_id}")
def check_crm_status(submission_id: str):
    """Check the status of a previously submitted enquiry.

    Re-submitting with the same submission_id triggers the idempotency
    check in the n8n workflow, so a dedicated status endpoint is not
    needed.
    """
    return JSONResponse(
        status_code=501,
        content={"error": "Status check not implemented. Re-submit with same submission_id for idempotent check."}
    )
