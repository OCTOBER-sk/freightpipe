"""Document ingestion — R2 upload, PDF validation, job creation (BACKEND.md §4.1, §7).

Handles:
- PDF validation (magic bytes + pdfplumber parse attempt)
- R2 upload (boto3 S3-compatible, Cloudflare R2 endpoint)
- Job creation with idempotency check
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg
import boto3
from botocore.config import Config as BotoConfig

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
# R2 Upload
# ---------------------------------------------------------------------------

def get_r2_client():
    """Create a boto3 S3 client configured for Cloudflare R2."""
    account_id = os.environ.get("R2_ACCOUNT_ID", "")
    access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")

    if not all([account_id, access_key, secret_key]):
        raise RuntimeError(
            "R2 credentials not configured. Set R2_ACCOUNT_ID, "
            "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY."
        )

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def upload_to_r2(
    data: bytes,
    key: str,
    content_type: str = "application/pdf",
) -> str:
    """Upload a file to R2. Returns the R2 key."""
    bucket = os.environ.get("R2_BUCKET_NAME", "freightpipe-docs")
    client = get_r2_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    logger.info("Uploaded %d bytes to R2: %s/%s", len(data), bucket, key)
    return key


def generate_r2_key(account_id: UUID, job_id: UUID, filename: str) -> str:
    """Generate a unique R2 key for an uploaded document."""
    # Sanitize: replace path separators and traversal sequences
    safe_name = filename.replace("/", "_").replace("\\", "_")
    safe_name = safe_name.replace("..", "_")
    return f"uploads/{account_id}/{job_id}/{safe_name}"


def generate_split_r2_key(
    account_id: UUID, job_id: UUID, doc_index: int
) -> str:
    """Generate an R2 key for a split document segment."""
    return f"uploads/{account_id}/{job_id}/split_{doc_index}.pdf"


def get_signed_url(r2_key: str, expires_in: int = 300) -> str:
    """Generate a time-limited signed URL for an R2 object."""
    bucket = os.environ.get("R2_BUCKET_NAME", "freightpipe-docs")
    client = get_r2_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": r2_key},
        ExpiresIn=expires_in,
    )


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
    """Create a job: validate PDF, upload to R2, insert job row.

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

    # 3. Create job row
    job = await jobs.create(
        conn,
        account_id=account_id,
        source_r2_key="",  # updated after R2 upload
        idempotency_key=idempotency_key,
        webhook_url=webhook_url,
        status="queued",
    )

    job_id = job["id"]

    # 4. Upload to R2
    r2_key = generate_r2_key(account_id, job_id, filename)
    try:
        upload_to_r2(pdf_data, r2_key)
    except Exception as e:
        # Update job to failed if R2 upload fails
        await jobs.update_status(conn, job_id, "failed", error={"r2_upload": str(e)})
        raise

    # 5. Update job with R2 key
    await jobs.update_status(conn, job_id, "queued")
    # Direct update for source_r2_key
    await conn.execute(
        "UPDATE jobs SET source_r2_key = $2 WHERE id = $1",
        job_id,
        r2_key,
    )

    return {
        "job_id": str(job_id),
        "status": "queued",
        "created_at": job["created_at"].isoformat() + "Z",
    }
