"""Documents repository — CRUD for the documents table."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import asyncpg


async def create(
    conn: asyncpg.Connection,
    *,
    job_id: UUID,
    page_start: int,
    page_end: int,
    doc_type: str | None = None,
    extraction_method: str | None = None,
    raw_text: str | None = None,
    classification_confidence: float | None = None,
) -> asyncpg.Record:
    """Create a new document record. Returns the inserted row."""
    doc_id = uuid4()
    now = datetime.utcnow()
    return await conn.fetchrow(
        """
        INSERT INTO documents (id, job_id, doc_type, page_start, page_end,
                               extraction_method, raw_text, classification_confidence, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """,
        doc_id,
        job_id,
        doc_type,
        page_start,
        page_end,
        extraction_method,
        raw_text,
        classification_confidence,
        now,
    )


async def get_by_id(conn: asyncpg.Connection, doc_id: UUID) -> asyncpg.Record | None:
    """Fetch a document by ID."""
    return await conn.fetchrow(
        "SELECT * FROM documents WHERE id = $1",
        doc_id,
    )


async def list_by_job(conn: asyncpg.Connection, job_id: UUID) -> list[asyncpg.Record]:
    """List all documents for a job, ordered by page_start."""
    return await conn.fetch(
        """
        SELECT * FROM documents
        WHERE job_id = $1
        ORDER BY page_start ASC
        """,
        job_id,
    )


async def update_classification(
    conn: asyncpg.Connection,
    doc_id: UUID,
    *,
    doc_type: str,
    classification_confidence: float,
) -> asyncpg.Record | None:
    """Update classification result for a document."""
    return await conn.fetchrow(
        """
        UPDATE documents
        SET doc_type = $2, classification_confidence = $3
        WHERE id = $1
        RETURNING *
        """,
        doc_id,
        doc_type,
        classification_confidence,
    )


async def update_extraction(
    conn: asyncpg.Connection,
    doc_id: UUID,
    *,
    extraction_method: str,
    raw_text: str | None = None,
) -> asyncpg.Record | None:
    """Update extraction method and raw text for a document."""
    return await conn.fetchrow(
        """
        UPDATE documents
        SET extraction_method = $2, raw_text = $3
        WHERE id = $1
        RETURNING *
        """,
        doc_id,
        extraction_method,
        raw_text,
    )


async def delete(conn: asyncpg.Connection, doc_id: UUID) -> bool:
    """Delete a document. Returns True if a row was deleted."""
    result = await conn.execute(
        "DELETE FROM documents WHERE id = $1",
        doc_id,
    )
    return result == "DELETE 1"


async def count_by_job(conn: asyncpg.Connection, job_id: UUID) -> int:
    """Count documents for a job."""
    row = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM documents WHERE job_id = $1",
        job_id,
    )
    return row["cnt"]
