"""CRM client for n8n webhook integration.

This module handles communication with the n8n webhook that forwards
leads to Odoo CRM via JSON-RPC.
"""

import os
import logging
import time
from typing import Optional
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from retrieval_service.src.api.schemas import Enquiry, CrmResponse

logger = logging.getLogger(__name__)


@dataclass
class CrmClientConfig:
    """Configuration for CRM client."""
    webhook_url: str
    webhook_token: str
    max_retries: int = 3
    base_timeout: float = 30.0
    backoff_factor: float = 2.0


class CrmClientError(Exception):
    """Base exception for CRM client errors."""
    def __init__(self, message: str, status_code: int = 500, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class CrmClient:
    """Client for submitting leads to CRM via n8n webhook.

    Handles retries with exponential backoff for transient failures
    (crm_unavailable). Validates responses and maps them to CrmResponse.
    """

    def __init__(self, config: Optional[CrmClientConfig] = None):
        """Initialize CRM client with configuration.

        Args:
            config: Optional CrmClientConfig. If not provided, reads from environment.
        """
        if config is None:
            config = CrmClientConfig(
                webhook_url=os.getenv("N8N_WEBHOOK_URL", ""),
                webhook_token=os.getenv("WEBHOOK_TOKEN", ""),
                max_retries=int(os.getenv("CRM_MAX_RETRIES", "3")),
                base_timeout=float(os.getenv("CRM_BASE_TIMEOUT", "30.0")),
                backoff_factor=float(os.getenv("CRM_BACKOFF_FACTOR", "2.0")),
            )

        if not config.webhook_url:
            raise CrmClientError(
                "N8N_WEBHOOK_URL not configured",
                status_code=500,
                retryable=False
            )
        if not config.webhook_token:
            raise CrmClientError(
                "WEBHOOK_TOKEN not configured",
                status_code=500,
                retryable=False
            )

        self.config = config
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.config.base_timeout),
                headers={
                    "Content-Type": "application/json",
                    "X-7didan-Token": self.config.webhook_token,
                }
            )
        return self._client

    def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def submit_enquiry(self, enquiry: Enquiry) -> CrmResponse:
        """Submit an enquiry to CRM via n8n webhook.

        Implements retry logic with exponential backoff for crm_unavailable errors.
        Validates consent before sending.

        Args:
            enquiry: The Enquiry to submit.

        Returns:
            CrmResponse with status, crm_id, verified flag, and any errors.

        Raises:
            CrmClientError: For configuration errors or non-retryable failures.
        """
        # Validate consent before any network call
        if not enquiry.consent:
            logger.warning("Consent declined for submission %s", enquiry.submission_id)
            return CrmResponse(
                status="consent_declined",
                submission_id=enquiry.submission_id,
                verified=False,
                retryable=False,
                errors=["Consent must be true to submit to CRM"]
            )

        payload = enquiry.to_payload()
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._post_with_timeout(payload)
                crm_response = self._parse_response(response, enquiry.submission_id)

                # If successful or non-retryable error, return immediately
                if crm_response.status != "crm_unavailable" or not crm_response.retryable:
                    return crm_response

                # crm_unavailable with retryable=True - retry with backoff
                last_error = CrmClientError(
                    f"CRM unavailable (attempt {attempt + 1}/{self.config.max_retries + 1})",
                    status_code=503,
                    retryable=True
                )
                logger.warning(
                    "CRM unavailable for submission %s, attempt %d/%d",
                    enquiry.submission_id, attempt + 1, self.config.max_retries + 1
                )

            except httpx.TimeoutException as e:
                last_error = CrmClientError(
                    f"Request timeout: {e}",
                    status_code=503,
                    retryable=True
                )
                logger.warning(
                    "Timeout submitting submission %s, attempt %d/%d",
                    enquiry.submission_id, attempt + 1, self.config.max_retries + 1
                )

            except httpx.RequestError as e:
                last_error = CrmClientError(
                    f"Request failed: {e}",
                    status_code=503,
                    retryable=True
                )
                logger.warning(
                    "Request error for submission %s, attempt %d/%d: %s",
                    enquiry.submission_id, attempt + 1, self.config.max_retries + 1, e
                )

            except ValidationError as e:
                # Response validation failed - non-retryable
                logger.error("Invalid CRM response for submission %s: %s", enquiry.submission_id, e)
                return CrmResponse(
                    status="crm_error",
                    submission_id=enquiry.submission_id,
                    verified=False,
                    retryable=False,
                    errors=[f"Invalid response from CRM: {e}"]
                )

            # Wait before retry with exponential backoff
            if attempt < self.config.max_retries:
                wait_time = self.config.backoff_factor ** attempt
                logger.info("Waiting %.1fs before retry...", wait_time)
                time.sleep(wait_time)

        # All retries exhausted
        logger.error(
            "All retries exhausted for submission %s: %s",
            enquiry.submission_id, last_error
        )
        return CrmResponse(
            status="crm_unavailable",
            submission_id=enquiry.submission_id,
            verified=False,
            retryable=True,
            errors=[str(last_error)] if last_error else ["Max retries exceeded"]
        )

    def _post_with_timeout(self, payload: dict) -> httpx.Response:
        """POST payload to n8n webhook with timeout."""
        client = self._get_client()
        response = client.post(self.config.webhook_url, json=payload)
        response.raise_for_status()
        return response

    def _parse_response(self, response: httpx.Response, submission_id: str) -> CrmResponse:
        """Parse and validate HTTP response from n8n webhook."""
        try:
            data = response.json()
        except ValueError as e:
            logger.error("Non-JSON response from CRM: %s", e)
            return CrmResponse(
                status="crm_error",
                submission_id=submission_id,
                verified=False,
                retryable=False,
                errors=["Invalid JSON response from CRM"]
            )

        # Validate required fields
        if "status" not in data:
            logger.error("Missing 'status' in CRM response: %s", data)
            return CrmResponse(
                status="crm_error",
                submission_id=submission_id,
                verified=False,
                retryable=False,
                errors=["Missing status in CRM response"]
            )

        # Ensure submission_id matches
        if data.get("submission_id") != submission_id:
            logger.warning(
                "Submission ID mismatch: expected %s, got %s",
                submission_id, data.get("submission_id")
            )
            data["submission_id"] = submission_id

        try:
            return CrmResponse(**data)
        except ValidationError as e:
            logger.error("CRM response validation failed: %s", e)
            return CrmResponse(
                status="crm_error",
                submission_id=submission_id,
                verified=False,
                retryable=False,
                errors=[f"Response validation failed: {e}"]
            )


def create_crm_client() -> CrmClient:
    """Factory function to create a configured CRM client."""
    return CrmClient()