"""FreightPipe API routes — all 18 endpoints from BACKEND.md §4.1."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from freightpipe.api.auth import get_account_id
from freightpipe.api.auth_jwt import create_access_token, hash_password, verify_password
from freightpipe.api.rate_limit import check_rate_limit
from freightpipe.api.webhooks import dispatch_webhook, test_webhook
from freightpipe.db.connection import get_pool
from freightpipe.db.repos import (
    accounts as accounts_repo,
    api_keys as api_keys_repo,
    documents as documents_repo,
    extracted_fields as extracted_fields_repo,
    jobs as jobs_repo,
    match_results as match_results_repo,
    provider_usage_log as provider_usage_log_repo,
    review_queue as review_queue_repo,
    users as users_repo,
)
from freightpipe.utils.config import MAX_UPLOAD_SIZE_MB

router = APIRouter(prefix="/v1")


def _error(code: str, message: str, request_id: str = "unknown") -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


# ---------------------------------------------------------------------------
# 1. POST /v1/documents — submit PDF (multipart/form-data)
# ---------------------------------------------------------------------------

@router.post("/documents", status_code=202)
async def submit_document(
    request: Request,
    file: UploadFile = File(...),
    webhook_url: str | None = None,
    account_id: UUID = Depends(get_account_id),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    check_rate_limit(account_id, request)

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=_error("file_too_large", f"File exceeds {MAX_UPLOAD_SIZE_MB}MB limit.", _request_id(request)),
        )

    if not content[:4] == b"%PDF":
        raise HTTPException(
            status_code=400,
            detail=_error("invalid_pdf", "The uploaded file could not be parsed as a PDF.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        if idempotency_key:
            existing = await jobs_repo.get_by_idempotency_key(conn, account_id, idempotency_key)
            if existing:
                return JSONResponse(
                    status_code=200,
                    content={
                        "job_id": str(existing["id"]),
                        "status": existing["status"],
                        "created_at": existing["created_at"].isoformat(),
                        "idempotent_replay": True,
                    },
                )

        source_filename = file.filename or "upload.pdf"
        try:
            job = await jobs_repo.create(
                conn,
                account_id=account_id,
                source_filename=source_filename,
                pdf_data=content,
                idempotency_key=idempotency_key,
                webhook_url=webhook_url,
            )
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail=_error("idempotency_conflict", "Duplicate idempotency key.", _request_id(request)),
                )
            raise

    return JSONResponse(
        status_code=202,
        content={
            "job_id": str(job["id"]),
            "status": job["status"],
            "created_at": job["created_at"].isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# 2. GET /v1/jobs — list jobs (paginated, filterable by status)
# ---------------------------------------------------------------------------

@router.get("/jobs")
async def list_jobs(
    request: Request,
    account_id: UUID = Depends(get_account_id),
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await jobs_repo.list_by_account(
            conn, account_id, status=status, limit=limit, cursor=cursor,
        )

    items = []
    for r in rows:
        doc_count = await _doc_count(r["id"])
        review_items = await _review_items_for_job(r["id"])
        items.append({
            "job_id": str(r["id"]),
            "status": r["status"],
            "shipment_id": str(r["shipment_id"]) if r["shipment_id"] else None,
            "document_count": doc_count,
            "review_required": len(review_items) > 0,
            "review_reasons": [ri["reason"] for ri in review_items],
            "created_at": r["created_at"].isoformat(),
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
        })

    next_cursor = None
    if len(rows) == limit:
        next_cursor = rows[-1]["created_at"].isoformat()

    return {"items": items, "next_cursor": next_cursor}


async def _doc_count(job_id: UUID) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await documents_repo.count_by_job(conn, job_id)


async def _review_items_for_job(job_id: UUID) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await review_queue_repo.list_by_job(conn, job_id)


# ---------------------------------------------------------------------------
# 3. GET /v1/jobs/{job_id} — poll job status
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        job = await jobs_repo.get_by_id(conn, job_id)

    if job is None or job["account_id"] != account_id:
        raise HTTPException(
            status_code=404,
            detail=_error("job_not_found", "Job not found.", _request_id(request)),
        )

    docs = await _docs_for_job(job_id)

    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        "shipment_id": str(job["shipment_id"]) if job["shipment_id"] else None,
        "documents": docs,
        "created_at": job["created_at"].isoformat(),
        "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
    }


async def _docs_for_job(job_id: UUID) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await documents_repo.list_by_job(conn, job_id)
    return [
        {
            "document_id": str(r["id"]),
            "doc_type": r["doc_type"],
            "page_start": r["page_start"],
            "page_end": r["page_end"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 4. GET /v1/jobs/{job_id}/result — full structured output
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}/result")
async def get_job_result(
    job_id: UUID,
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        job = await jobs_repo.get_by_id(conn, job_id)

    if job is None or job["account_id"] != account_id:
        raise HTTPException(
            status_code=404,
            detail=_error("job_not_found", "Job not found.", _request_id(request)),
        )

    if job["status"] not in ("complete", "needs_review"):
        raise HTTPException(
            status_code=409,
            detail=_error("job_not_complete", f"Job is not yet complete. Current status: {job['status']}", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        doc_rows = await documents_repo.list_by_job(conn, job_id)
        documents_out = []
        for d in doc_rows:
            fields = await extracted_fields_repo.list_by_document(conn, d["id"])
            fields_out = {}
            for f in fields:
                value = f["field_value"]
                try:
                    value = json.loads(value) if value else None
                except (json.JSONDecodeError, TypeError):
                    pass
                fields_out[f["field_name"]] = {
                    "value": value,
                    "confidence": float(f["confidence"]),
                    "source": {
                        "page": f["source_page"],
                        "bbox": f["source_bbox"] if f["source_bbox"] else None,
                    },
                }
            doc_conf = float(d["classification_confidence"]) if d["classification_confidence"] else None
            documents_out.append({
                "document_id": str(d["id"]),
                "doc_type": d["doc_type"],
                "fields": fields_out,
                "document_confidence": doc_conf,
            })

        match_rows = []
        if job["shipment_id"]:
            match_rows = await match_results_repo.list_by_shipment(conn, job["shipment_id"])

    match_out = [
        {
            "line_item": m["line_item"],
            "rate_con_value": m["rate_con_value"],
            "bol_pod_value": m["bol_pod_value"],
            "invoice_value": m["invoice_value"],
            "discrepancy_flag": m["discrepancy_flag"],
            "discrepancy_amount": float(m["discrepancy_amount"]) if m["discrepancy_amount"] else None,
        }
        for m in match_rows
    ]

    review_items = await _review_items_for_job(job_id)
    review_reasons = []
    for ri in review_items:
        if ri["reason"] == "discrepancy":
            for m in match_rows:
                if m["discrepancy_flag"] != "none":
                    review_reasons.append(f"discrepancy: {m['discrepancy_flag']} on {m['line_item']}")
        else:
            review_reasons.append(ri["reason"])

    return {
        "job_id": str(job["id"]),
        "shipment_id": str(job["shipment_id"]) if job["shipment_id"] else None,
        "documents": documents_out,
        "match_results": match_out,
        "review_required": len(review_items) > 0,
        "review_reasons": review_reasons,
    }


# ---------------------------------------------------------------------------
# 5. GET /v1/review-queue — list review items
# ---------------------------------------------------------------------------

@router.get("/review-queue")
async def list_review_queue(
    request: Request,
    account_id: UUID = Depends(get_account_id),
    state: str = "pending",
    reason: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await review_queue_repo.list_paginated(
            conn, state=state, reason=reason, limit=limit, cursor=cursor,
        )

    items = []
    for r in rows:
        job = await _get_job_if_owned(r["job_id"], account_id)
        if job is None:
            continue
        items.append({
            "id": str(r["id"]),
            "job_id": str(r["job_id"]),
            "reason": r["reason"],
            "state": r["state"],
            "assigned_to": r["assigned_to"],
            "resolution_notes": r["resolution_notes"],
            "created_at": r["created_at"].isoformat(),
            "resolved_at": r["resolved_at"].isoformat() if r["resolved_at"] else None,
        })

    next_cursor = None
    if len(rows) == limit:
        next_cursor = rows[-1]["created_at"].isoformat()

    return {"items": items, "next_cursor": next_cursor}


async def _get_job_if_owned(job_id: UUID, account_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        job = await jobs_repo.get_by_id(conn, job_id)
    if job and job["account_id"] == account_id:
        return job
    return None


# ---------------------------------------------------------------------------
# 6. POST /v1/review-queue/{item_id}/resolve
# ---------------------------------------------------------------------------

@router.post("/review-queue/{item_id}/resolve")
async def resolve_review_item(
    item_id: UUID,
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    body = await request.json()
    resolution = body.get("resolution")
    if resolution not in ("approved", "corrected", "escalated"):
        raise HTTPException(
            status_code=400,
            detail=_error("internal_error", "resolution must be approved, corrected, or escalated.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await review_queue_repo.get_by_id(conn, item_id)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=_error("job_not_found", "Review item not found.", _request_id(request)),
            )

        job = await jobs_repo.get_by_id(conn, item["job_id"])
        if job is None or job["account_id"] != account_id:
            raise HTTPException(
                status_code=404,
                detail=_error("job_not_found", "Review item not found.", _request_id(request)),
            )

        updated = await review_queue_repo.resolve(
            conn,
            item_id,
            resolution=resolution,
            resolution_notes=body.get("notes"),
        )

        if resolution in ("approved", "corrected"):
            await jobs_repo.update_status(conn, item["job_id"], "complete")

    webhook_url = job["webhook_url"]
    if webhook_url:
        await dispatch_webhook(
            webhook_url,
            event="review.resolved",
            job_id=item["job_id"],
            account_id=account_id,
            data={"review_item_id": str(item_id), "resolution": resolution},
        )

    return {
        "id": str(updated["id"]),
        "job_id": str(updated["job_id"]),
        "reason": updated["reason"],
        "state": updated["state"],
        "assigned_to": updated["assigned_to"],
        "resolution_notes": updated["resolution_notes"],
        "created_at": updated["created_at"].isoformat(),
        "resolved_at": updated["resolved_at"].isoformat() if updated["resolved_at"] else None,
    }


# ---------------------------------------------------------------------------
# 7. GET /v1/documents/{document_id}/pdf — return PDF from Postgres BYTEA
# ---------------------------------------------------------------------------

@router.get("/documents/{document_id}/pdf")
async def get_document_pdf(
    document_id: UUID,
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        doc = await documents_repo.get_by_id(conn, document_id)

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=_error("job_not_found", "Document not found.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        job = await jobs_repo.get_by_id(conn, doc["job_id"])

    if job is None or job["account_id"] != account_id:
        raise HTTPException(
            status_code=404,
            detail=_error("job_not_found", "Document not found.", _request_id(request)),
        )

    pdf_data = job.get("pdf_data")
    if not pdf_data:
        raise HTTPException(
            status_code=404,
            detail=_error("pdf_not_found", "PDF data not found for this job.", _request_id(request)),
        )

    return Response(content=bytes(pdf_data), media_type="application/pdf")


# ---------------------------------------------------------------------------
# 8. POST /v1/webhooks/test — test webhook delivery
# ---------------------------------------------------------------------------

@router.post("/webhooks/test")
async def test_webhook_endpoint(
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    body = await request.json()
    webhook_url = body.get("webhook_url")
    if not webhook_url:
        raise HTTPException(
            status_code=400,
            detail=_error("internal_error", "webhook_url is required.", _request_id(request)),
        )

    result = await test_webhook(webhook_url)
    return result


# ---------------------------------------------------------------------------
# 9. GET /v1/health — liveness check (unauthenticated)
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check():
    return {"worker": "ok", "processor": "ok"}


# ---------------------------------------------------------------------------
# Auth endpoints — register, login, me, profile
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/auth/register", status_code=201)
async def register(request: Request):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    phone = body.get("phone")
    company_name = (body.get("company_name") or "").strip()
    password = body.get("password") or ""

    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(
            status_code=400,
            detail=_error("validation_error", "Invalid email format.", _request_id(request)),
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail=_error("validation_error", "Password must be at least 8 characters.", _request_id(request)),
        )
    if not company_name:
        raise HTTPException(
            status_code=400,
            detail=_error("validation_error", "company_name is required.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await users_repo.get_by_email(conn, email)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=_error("email_taken", "Email already registered.", _request_id(request)),
            )

        pw_hash = hash_password(password)
        user = await users_repo.create(
            conn, email=email, phone=phone, company_name=company_name, password_hash=pw_hash,
        )

        account = await accounts_repo.create(conn, name=company_name)
        account_id = account["id"]

        await conn.execute(
            "UPDATE accounts SET user_id = $1 WHERE id = $2",
            user["id"], account_id,
        )

        raw_key = f"fp_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key_row = await api_keys_repo.create(
            conn, account_id=account_id, key_hash=key_hash, label="Primary Key",
        )

    token = create_access_token(user["id"], account_id)

    return JSONResponse(
        status_code=201,
        content={
            "user_id": str(user["id"]),
            "account_id": str(account_id),
            "token": token,
            "api_key": raw_key,
        },
    )


@router.post("/auth/login")
async def login(request: Request):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not email or not password:
        raise HTTPException(
            status_code=400,
            detail=_error("validation_error", "email and password are required.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await users_repo.get_by_email(conn, email)
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(
                status_code=401,
                detail=_error("invalid_credentials", "Invalid email or password.", _request_id(request)),
            )
        if not user["is_active"]:
            raise HTTPException(
                status_code=403,
                detail=_error("account_disabled", "Account is disabled.", _request_id(request)),
            )

        account_row = await conn.fetchrow(
            "SELECT id FROM accounts WHERE user_id = $1 LIMIT 1",
            user["id"],
        )
        account_id = account_row["id"] if account_row else None

    token = create_access_token(user["id"], account_id)

    return {
        "user_id": str(user["id"]),
        "account_id": str(account_id),
        "token": token,
    }


@router.get("/auth/me")
async def get_me(request: Request, account_id: UUID = Depends(get_account_id)):
    # Extract user_id from JWT — re-decode token
    auth_header = request.headers.get("authorization", "")
    user_id = None
    if auth_header.startswith("Bearer "):
        from freightpipe.api.auth_jwt import decode_access_token
        try:
            payload = decode_access_token(auth_header[7:])
            user_id = UUID(payload.get("sub"))
        except (ValueError, KeyError):
            pass

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail=_error("unauthorized", "JWT token required for this endpoint.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await users_repo.get_by_id(conn, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail=_error("user_not_found", "User not found.", _request_id(request)),
        )

    return {
        "user_id": str(user["id"]),
        "email": user["email"],
        "phone": user["phone"],
        "company_name": user["company_name"],
        "created_at": user["created_at"].isoformat(),
    }


@router.put("/auth/profile")
async def update_profile(request: Request, account_id: UUID = Depends(get_account_id)):
    auth_header = request.headers.get("authorization", "")
    user_id = None
    if auth_header.startswith("Bearer "):
        from freightpipe.api.auth_jwt import decode_access_token
        try:
            payload = decode_access_token(auth_header[7:])
            user_id = UUID(payload.get("sub"))
        except (ValueError, KeyError):
            pass

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail=_error("unauthorized", "JWT token required for this endpoint.", _request_id(request)),
        )

    body = await request.json()
    phone = body.get("phone")
    company_name = body.get("company_name")

    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await users_repo.update_profile(
            conn, user_id, phone=phone, company_name=company_name,
        )

    if not user:
        raise HTTPException(
            status_code=404,
            detail=_error("user_not_found", "User not found.", _request_id(request)),
        )

    return {
        "user_id": str(user["id"]),
        "email": user["email"],
        "phone": user["phone"],
        "company_name": user["company_name"],
        "created_at": user["created_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# 10. GET /v1/api-keys — list keys (masked)
# ---------------------------------------------------------------------------

@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await api_keys_repo.list_by_account(conn, account_id)

    items = []
    for r in rows:
        key_hash = r["key_hash"]
        key_prefix = f"fp_live_{key_hash[:4]}"
        items.append({
            "id": str(r["id"]),
            "label": r["label"],
            "key_prefix": key_prefix,
            "created_at": r["created_at"].isoformat(),
            "revoked_at": r["revoked_at"].isoformat() if r["revoked_at"] else None,
        })

    return {"items": items}


# ---------------------------------------------------------------------------
# 10.5 POST /v1/bootstrap — create first account + API key (no auth required, one-time only)
# ---------------------------------------------------------------------------

@router.post("/bootstrap", status_code=201)
async def bootstrap_account(request: Request):
    """Create the first account and API key. Only works if no accounts exist yet."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT COUNT(*) FROM accounts")
        if existing > 0:
            raise HTTPException(
                status_code=409,
                detail=_error("idempotency_conflict", "Account already exists. Use existing API key.", _request_id(request)),
            )

        body = await request.json()
        account_name = body.get("name", "Default Account")

        # Create account
        account = await accounts_repo.create(conn, name=account_name)
        account_id = account["id"]

        # Create API key
        raw_key = f"fp_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        label = body.get("label", "Primary Key")
        key_row = await api_keys_repo.create(conn, account_id=account_id, key_hash=key_hash, label=label)

    return {
        "account_id": str(account_id),
        "key": raw_key,
        "key_id": str(key_row["id"]),
        "label": label,
        "message": "Save this key — it cannot be retrieved again.",
    }


# ---------------------------------------------------------------------------
# 11. POST /v1/api-keys — create key (raw key shown once)
# ---------------------------------------------------------------------------

@router.post("/api-keys", status_code=201)
async def create_api_key(
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    body = await request.json()
    label = body.get("label")

    raw_key = f"fp_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await api_keys_repo.create(conn, account_id=account_id, key_hash=key_hash, label=label)

    return {
        "id": str(row["id"]),
        "label": row["label"],
        "key": raw_key,
        "created_at": row["created_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# 12. DELETE /v1/api-keys/{key_id} — revoke key
# ---------------------------------------------------------------------------

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        key_row = await api_keys_repo.get_by_id(conn, key_id)

    if key_row is None or key_row["account_id"] != account_id:
        raise HTTPException(
            status_code=404,
            detail=_error("job_not_found", "API key not found.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        updated = await api_keys_repo.revoke(conn, key_id)

    return {
        "id": str(updated["id"]),
        "revoked_at": updated["revoked_at"].isoformat() if updated["revoked_at"] else None,
    }


# ---------------------------------------------------------------------------
# 13. GET /v1/settings/webhook — get account-level webhook config
# ---------------------------------------------------------------------------

@router.get("/settings/webhook")
async def get_webhook_settings(
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        account = await accounts_repo.get_by_id(conn, account_id)

    if account is None:
        raise HTTPException(
            status_code=404,
            detail=_error("job_not_found", "Account not found.", _request_id(request)),
        )

    byok_raw = account["llm_byok_keys"] or "{}"
    byok = json.loads(byok_raw) if isinstance(byok_raw, str) else byok_raw
    webhook_url = byok.get("webhook_url")
    webhook_secret = byok.get("webhook_secret")

    if not webhook_url:
        raise HTTPException(
            status_code=404,
            detail=_error("job_not_found", "No webhook configured for this account.", _request_id(request)),
        )

    return {
        "webhook_url": webhook_url,
        "webhook_secret": webhook_secret or "",
        "updated_at": account["created_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# 14. PUT /v1/settings/webhook — set/update webhook config
# ---------------------------------------------------------------------------

@router.put("/settings/webhook")
async def update_webhook_settings(
    request: Request,
    account_id: UUID = Depends(get_account_id),
):
    body = await request.json()
    webhook_url = body.get("webhook_url")
    if not webhook_url:
        raise HTTPException(
            status_code=400,
            detail=_error("internal_error", "webhook_url is required.", _request_id(request)),
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        account = await accounts_repo.get_by_id(conn, account_id)
        byok_raw = account["llm_byok_keys"] or "{}"
        byok = dict(json.loads(byok_raw) if isinstance(byok_raw, str) else byok_raw)
        byok["webhook_url"] = webhook_url
        if "webhook_secret" not in byok:
            byok["webhook_secret"] = f"whsec_{secrets.token_urlsafe(32)}"
        await accounts_repo.update_byok_keys(conn, account_id, byok)

    return {
        "webhook_url": webhook_url,
        "webhook_secret": byok["webhook_secret"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# 15. GET /v1/analytics/usage — usage metrics
# ---------------------------------------------------------------------------

@router.get("/analytics/usage")
async def get_usage_analytics(
    request: Request,
    account_id: UUID = Depends(get_account_id),
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
):
    days = int(period.replace("d", ""))
    start_date = date.today() - timedelta(days=days)
    end_date = date.today()

    pool = await get_pool()
    async with pool.acquire() as conn:
        usage_rows = await provider_usage_log_repo.get_by_date_range(
            conn, start_date=start_date, end_date=end_date,
        )

        job_rows = await jobs_repo.list_by_account(conn, account_id, limit=10000)

    total_jobs = len(job_rows)
    completed = sum(1 for j in job_rows if j["status"] == "complete")
    needs_review = sum(1 for j in job_rows if j["status"] == "needs_review")
    failed = sum(1 for j in job_rows if j["status"] == "failed")

    total_calls = sum(r["request_count"] for r in usage_rows)
    cache_hits = sum(r["cache_hit_count"] for r in usage_rows)
    cache_hit_rate = cache_hits / total_calls if total_calls > 0 else 0.0

    by_provider: dict[str, int] = {}
    for r in usage_rows:
        by_provider[r["provider"]] = by_provider.get(r["provider"], 0) + r["request_count"]

    return {
        "period": period,
        "jobs": {
            "total": total_jobs,
            "completed": completed,
            "needs_review": needs_review,
            "failed": failed,
        },
        "documents": {"total": 0, "by_type": {}},
        "accuracy": {"avg_confidence": 0.0, "review_rate": 0.0, "correction_rate": 0.0},
        "processing_time": {"p50_seconds": 0, "p90_seconds": 0, "p99_seconds": 0},
        "llm_usage": {
            "total_calls": total_calls,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "by_provider": by_provider,
        },
    }
