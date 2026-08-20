"""Webhook dispatch with HMAC signing (BACKEND.md §4.2)."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from uuid import UUID

import httpx


def _sign_payload(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def dispatch_webhook(
    webhook_url: str,
    *,
    event: str,
    job_id: UUID,
    account_id: UUID,
    data: dict | None = None,
    webhook_secret: str | None = None,
) -> dict:
    """Dispatch a webhook event to the configured URL.

    Returns {"delivered": True, "status_code": ...} on success,
    or {"delivered": False, "error": "..."} on failure.
    """
    secret = webhook_secret or os.environ.get("WEBHOOK_HMAC_SECRET", "")
    payload = {
        "event": event,
        "job_id": str(job_id),
        "account_id": str(account_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data or {},
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if secret:
        headers["X-FreightPipe-Signature"] = _sign_payload(body, secret)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, content=body, headers=headers)
            return {"delivered": resp.status_code < 400, "status_code": resp.status_code}
    except Exception as exc:
        return {"delivered": False, "error": str(exc)}


async def test_webhook(webhook_url: str) -> dict:
    """Send a test payload to verify webhook connectivity.

    Returns {"delivered": True, "status_code": ...} or {"delivered": False, "error": "..."}.
    """
    payload = {
        "event": "webhook.test",
        "job_id": "00000000-0000-0000-0000-000000000000",
        "account_id": "00000000-0000-0000-0000-000000000000",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "This is a test webhook from FreightPipe."},
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    secret = os.environ.get("WEBHOOK_HMAC_SECRET", "")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if secret:
        headers["X-FreightPipe-Signature"] = _sign_payload(body, secret)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, content=body, headers=headers)
            return {"delivered": resp.status_code < 400, "status_code": resp.status_code}
    except Exception as exc:
        return {"delivered": False, "error": str(exc)}
