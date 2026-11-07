"""Client for the n8n enquiry webhook. Standard library only.

The backend must show success to the visitor only when `CrmResult.ok` is true, which
means n8n read the opportunity back from Odoo and it matched what was sent.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from backend.crm.contract import Enquiry

OK_STATUSES = {"created", "duplicate"}


@dataclass(frozen=True)
class CrmResult:
    http_status: int
    status: str
    submission_id: str | None = None
    crm_id: int | None = None
    verified: bool = False
    retryable: bool = False
    errors: list[str] = field(default_factory=list)
    attempts: int = 1

    @property
    def ok(self) -> bool:
        return self.status in OK_STATUSES and self.verified


class CrmClient:
    def __init__(self, webhook_url: str, token: str, timeout: float = 30.0, max_attempts: int = 3, backoff: float = 1.5):
        self.webhook_url, self.token = webhook_url, token
        self.timeout, self.max_attempts, self.backoff = timeout, max_attempts, backoff

    def submit(self, enquiry: Enquiry) -> CrmResult:
        """Send the enquiry; retry only retryable failures, always with the same submission_id.

        Retrying is safe because the workflow looks the submission ID up in Odoo before creating.
        """
        result = None
        for attempt in range(1, self.max_attempts + 1):
            result = self._post(enquiry.to_payload(), attempt)
            if not result.retryable or attempt == self.max_attempts:
                return result
            time.sleep(self.backoff * attempt)
        return result

    def _post(self, payload: dict, attempt: int) -> CrmResult:
        request = urllib.request.Request(
            self.webhook_url, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "X-7didan-Token": self.token},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                return self._parse(resp.status, resp.read(), attempt)
        except urllib.error.HTTPError as err:
            return self._parse(err.code, err.read(), attempt)
        except (urllib.error.URLError, TimeoutError) as err:
            reason = getattr(err, "reason", err)
            return CrmResult(0, "unreachable", payload.get("submission_id"), retryable=True,
                             errors=[f"n8n webhook unreachable: {reason}"], attempts=attempt)

    @staticmethod
    def _parse(http_status: int, raw: bytes, attempt: int) -> CrmResult:
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            body = {"status": "bad_response", "errors": [raw[:200].decode("utf-8", "replace")]}
        return CrmResult(
            http_status=http_status, status=body.get("status", "bad_response"),
            submission_id=body.get("submission_id"), crm_id=body.get("crm_id"),
            verified=bool(body.get("verified")),
            # A gateway error without a workflow answer (n8n itself failing) is worth retrying too.
            retryable=bool(body.get("retryable")) or (http_status in (502, 503, 504) and "status" not in body),
            errors=list(body.get("errors") or []), attempts=attempt,
        )
