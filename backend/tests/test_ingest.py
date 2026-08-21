"""Tests for document ingestion — PDF validation, job creation."""
from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from freightpipe.pipeline.ingest import (
    validate_pdf_magic,
    validate_pdf_parse,
    validate_pdf,
    PDFValidationError,
    IdempotencyConflictError,
    MAX_UPLOAD_BYTES,
)


# ---------------------------------------------------------------------------
# PDF magic bytes tests
# ---------------------------------------------------------------------------

class TestPDFMagic:
    def test_valid_pdf_magic(self):
        data = b"%PDF-1.4 some content"
        assert validate_pdf_magic(data) is True

    def test_invalid_magic(self):
        data = b"PK\x03\x04 not a pdf"
        assert validate_pdf_magic(data) is False

    def test_empty_file(self):
        assert validate_pdf_magic(b"") is False

    def test_partial_magic(self):
        assert validate_pdf_magic(b"%PD") is False


# ---------------------------------------------------------------------------
# PDF validation tests
# ---------------------------------------------------------------------------

class TestPDFValidation:
    def test_empty_file_raises(self):
        with pytest.raises(PDFValidationError) as exc_info:
            validate_pdf(b"")
        assert exc_info.value.code == "invalid_pdf"
        assert "empty" in str(exc_info.value).lower()

    def test_oversized_file_raises(self):
        # Create data larger than max
        data = b"%PDF-1.4" + b"x" * (MAX_UPLOAD_BYTES + 1)
        with pytest.raises(PDFValidationError) as exc_info:
            validate_pdf(data)
        assert exc_info.value.code == "file_too_large"

    def test_non_pdf_magic_raises(self):
        data = b"not a pdf file at all"
        with pytest.raises(PDFValidationError) as exc_info:
            validate_pdf(data)
        assert exc_info.value.code == "invalid_pdf"

    def test_valid_pdf_magic_but_corrupt_content(self):
        # Has PDF magic but can't be parsed
        data = b"%PDF-1.4 this is not valid pdf content"
        with pytest.raises(PDFValidationError):
            validate_pdf(data)


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_idempotency_conflict_error(self):
        existing = {"id": str(uuid4()), "status": "queued"}
        err = IdempotencyConflictError(existing)
        assert err.existing_job == existing
        assert str(uuid4())[:8] not in str(err)  # just checking it doesn't crash


# ---------------------------------------------------------------------------
# Job creation integration tests (mocked DB)
# ---------------------------------------------------------------------------

class TestCreateJob:
    @pytest.mark.asyncio
    async def test_create_job_success(self, mock_conn, account_id):
        """Test successful job creation with mocked DB."""
        job_id = uuid4()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": job_id,
            "account_id": account_id,
            "status": "queued",
            "created_at": __import__("datetime").datetime.utcnow(),
            "source_filename": "test.pdf",
            "pdf_data": b"%PDF-1.4 test",
        })

        with patch("freightpipe.pipeline.ingest.validate_pdf", return_value=(True, 1)):
            from freightpipe.pipeline.ingest import create_job
            result = await create_job(
                mock_conn,
                account_id=account_id,
                pdf_data=b"%PDF-1.4 test",
                filename="test.pdf",
            )

            assert result["status"] == "queued"
            assert "job_id" in result

    @pytest.mark.asyncio
    async def test_create_job_idempotency_conflict(self, mock_conn, account_id):
        """Test that duplicate idempotency key raises conflict."""
        existing_job = {
            "id": str(uuid4()),
            "account_id": str(account_id),
            "status": "queued",
        }
        mock_conn.fetchrow = AsyncMock(return_value=existing_job)

        from freightpipe.pipeline.ingest import create_job
        with pytest.raises(IdempotencyConflictError):
            await create_job(
                mock_conn,
                account_id=account_id,
                pdf_data=b"%PDF-1.4 test",
                filename="test.pdf",
                idempotency_key="duplicate-key",
            )

    @pytest.mark.asyncio
    async def test_create_job_invalid_pdf(self, mock_conn, account_id):
        """Test that invalid PDF raises validation error."""
        mock_conn.fetchrow = AsyncMock(return_value=None)  # No idempotency conflict

        from freightpipe.pipeline.ingest import create_job
        with pytest.raises(PDFValidationError):
            await create_job(
                mock_conn,
                account_id=account_id,
                pdf_data=b"not a pdf",
                filename="test.pdf",
            )
