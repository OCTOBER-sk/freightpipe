"""Extracted fields repository — CRUD for the extracted_fields table."""
from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg


async def create(
    conn: asyncpg.Connection,
    *,
    document_id: UUID,
    field_name: str,
    field_value: str | None = None,
    confidence: float,
    source_page: int | None = None,
    source_bbox: dict | None = None,
    extraction_method: str | None = None,
) -> asyncpg.Record:
    """Create a new extracted field. Returns the inserted row."""
    field_id = uuid4()
    now = datetime.utcnow()
    bbox_json = json.dumps(source_bbox) if source_bbox else None
    return await conn.fetchrow(
        """
        INSERT INTO extracted_fields (id, document_id, field_name, field_value, confidence,
                                      source_page, source_bbox, extraction_method, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
        RETURNING *
        """,
        field_id,
        document_id,
        field_name,
        field_value,
        confidence,
        source_page,
        bbox_json,
        extraction_method,
        now,
    )


async def get_by_id(conn: asyncpg.Connection, field_id: UUID) -> asyncpg.Record | None:
    """Fetch an extracted field by ID."""
    return await conn.fetchrow(
        "SELECT * FROM extracted_fields WHERE id = $1",
        field_id,
    )


async def list_by_document(
    conn: asyncpg.Connection,
    document_id: UUID,
) -> list[asyncpg.Record]:
    """List all extracted fields for a document."""
    return await conn.fetch(
        """
        SELECT * FROM extracted_fields
        WHERE document_id = $1
        ORDER BY field_name ASC
        """,
        document_id,
    )


async def list_by_document_and_name(
    conn: asyncpg.Connection,
    document_id: UUID,
    field_name: str,
) -> list[asyncpg.Record]:
    """List extracted fields for a document filtered by field name."""
    return await conn.fetch(
        """
        SELECT * FROM extracted_fields
        WHERE document_id = $1 AND field_name = $2
        ORDER BY created_at ASC
        """,
        document_id,
        field_name,
    )


async def update_value(
    conn: asyncpg.Connection,
    field_id: UUID,
    *,
    field_value: str,
    confidence: float,
) -> asyncpg.Record | None:
    """Update the value and confidence of an extracted field (used for review corrections)."""
    return await conn.fetchrow(
        """
        UPDATE extracted_fields
        SET field_value = $2, confidence = $3
        WHERE id = $1
        RETURNING *
        """,
        field_id,
        field_value,
        confidence,
    )


async def delete_by_document(conn: asyncpg.Connection, document_id: UUID) -> str:
    """Delete all extracted fields for a document."""
    return await conn.execute(
        "DELETE FROM extracted_fields WHERE document_id = $1",
        document_id,
    )


async def create_many(
    conn: asyncpg.Connection,
    fields: list[dict],
) -> list[asyncpg.Record]:
    """Bulk-insert extracted fields. Each dict needs document_id, field_name, confidence.
    Optional: field_value, source_page, source_bbox, extraction_method."""
    now = datetime.utcnow()
    records = []
    for f in fields:
        field_id = uuid4()
        bbox_json = json.dumps(f.get("source_bbox")) if f.get("source_bbox") else None
        row = await conn.fetchrow(
            """
            INSERT INTO extracted_fields (id, document_id, field_name, field_value, confidence,
                                          source_page, source_bbox, extraction_method, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
            RETURNING *
            """,
            field_id,
            f["document_id"],
            f["field_name"],
            f.get("field_value"),
            f["confidence"],
            f.get("source_page"),
            bbox_json,
            f.get("extraction_method"),
            now,
        )
        records.append(row)
    return records


async def get_by_document_id(
    conn: asyncpg.Connection,
    document_id: UUID,
) -> list[asyncpg.Record]:
    """Fetch all extracted fields for a document (alias for list_by_document)."""
    return await list_by_document(conn, document_id)


async def delete(conn: asyncpg.Connection, field_id: UUID) -> bool:
    """Delete a single extracted field."""
    result = await conn.execute(
        "DELETE FROM extracted_fields WHERE id = $1",
        field_id,
    )
    return result == "DELETE 1"
