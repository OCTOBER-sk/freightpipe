"""Document ingestion — PDF validation, job creation (BACKEND.md §4.1, §7).

Handles:
- PDF validation (magic bytes + pdfplumber parse attempt)
- Job creation with idempotency check
- PDF stored directly in Postgres (BYTEA)
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg

from freightpipe.db.repos import jobs, documents as docs_repo

logger = logging.getLogger(__name__)

# PDF magic bytes
PDF_MAGIC = b"%PDF"

# Max upload size (from config, default 25MB)
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# PDF Validation
# ---------------------------------------------------------------------------

class PDFValidationError(Exception):
    """Raised when uploaded file fails PDF validation."""
    def __init__(self, message: str, code: str = "invalid_pdf"):
        self.code = code
        super().__init__(message)


def validate_pdf_magic(data: bytes) -> bool:
    """Check if file starts with %PDF magic bytes."""
    return data[:4] == PDF_MAGIC


def validate_pdf_parse(data: bytes) -> tuple[bool, int]:
    """Attempt to parse PDF with pdfplumber. Returns (valid, page_count).

    Raises PDFValidationError if parsing fails completely.
    """
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            if page_count == 0:
                raise PDFValidationError(
                    "PDF contains no pages.",
                    code="invalid_pdf",
                )
            return True, page_count
    except PDFValidationError:
        raise
    except Exception as e:
        raise PDFValidationError(
            f"Could not parse PDF: {e}",
            code="invalid_pdf",
        )


def validate_pdf(data: bytes) -> tuple[bool, int]:
    """Full PDF validation: magic bytes + parse attempt.

    Returns (valid, page_count).
    Raises PDFValidationError on failure.
    """
    if len(data) == 0:
        raise PDFValidationError(
            "Uploaded file is empty.",
            code="invalid_pdf",
        )

    if len(data) > MAX_UPLOAD_BYTES:
        raise PDFValidationError(
            f"File exceeds maximum size of {MAX_UPLOAD_SIZE_MB}MB.",
            code="file_too_large",
        )

    if not validate_pdf_magic(data):
        raise PDFValidationError(
            "The uploaded file could not be parsed as a PDF.",
            code="invalid_pdf",
        )

    return validate_pdf_parse(data)


# ---------------------------------------------------------------------------
# Job Creation
# ---------------------------------------------------------------------------

class IdempotencyConflictError(Exception):
    """Raised when idempotency key conflicts with an existing job."""
    def __init__(self, existing_job: dict):
        self.existing_job = existing_job
        super().__init__(
            f"Idempotency key already used by job {existing_job.get('id')}"
        )


async def create_job(
    conn: asyncpg.Connection,
    *,
    account_id: UUID,
    pdf_data: bytes,
    filename: str,
    idempotency_key: str | None = None,
    webhook_url: str | None = None,
) -> dict:
    """Create a job: validate PDF, store in Postgres, insert job row.

    Returns dict with job_id, status, created_at.
    Raises IdempotencyConflictError if idempotency key already used.
    Raises PDFValidationError if PDF is invalid.
    """
    # 1. Idempotency check (BACKEND.md §4.4)
    if idempotency_key:
        existing = await jobs.get_by_idempotency_key(conn, account_id, idempotency_key)
        if existing:
            raise IdempotencyConflictError(dict(existing))

    # 2. Validate PDF
    validate_pdf(pdf_data)

    # 3. Create job row with PDF data stored in BYTEA column
    job = await jobs.create(
        conn,
        account_id=account_id,
        source_filename=filename,
        pdf_data=pdf_data,
        idempotency_key=idempotency_key,
        webhook_url=webhook_url,
        status="queued",
    )

    return {
        "job_id": str(job["id"]),
        "status": "queued",
        "created_at": job["created_at"].isoformat() + "Z",
    }
