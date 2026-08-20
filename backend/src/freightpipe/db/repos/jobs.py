"""Jobs repository — CRUD for the jobs table."""
from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg


async def create(
    conn: asyncpg.Connection,
    *,
    account_id: UUID,
    source_r2_key: str,
    idempotency_key: str | None = None,
    webhook_url: str | None = None,
    status: str = "queued",
) -> asyncpg.Record:
    """Create a new job. Returns the inserted row."""
    job_id = uuid4()
    now = datetime.utcnow()
    return await conn.fetchrow(
        """
        INSERT INTO jobs (id, account_id, idempotency_key, status, source_r2_key,
                          webhook_url, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
        RETURNING *
        """,
        job_id,
        account_id,
        idempotency_key,
        status,
        source_r2_key,
        webhook_url,
        now,
    )


async def get_by_id(conn: asyncpg.Connection, job_id: UUID) -> asyncpg.Record | None:
    """Fetch a job by ID."""
    return await conn.fetchrow(
        "SELECT * FROM jobs WHERE id = $1",
        job_id,
    )


async def get_by_idempotency_key(
    conn: asyncpg.Connection,
    account_id: UUID,
    idempotency_key: str,
) -> asyncpg.Record | None:
    """Fetch a job by account + idempotency key (for dedup)."""
    return await conn.fetchrow(
        """
        SELECT * FROM jobs
        WHERE account_id = $1 AND idempotency_key = $2
        """,
        account_id,
        idempotency_key,
    )


async def update_status(
    conn: asyncpg.Connection,
    job_id: UUID,
    status: str,
    *,
    error: dict | None = None,
    shipment_id: UUID | None = None,
) -> asyncpg.Record | None:
    """Update job status and optional fields. Returns updated row."""
    now = datetime.utcnow()
    completed_at = now if status in ("complete", "failed", "needs_review", "needs_llm_capacity") else None
    error_json = json.dumps(error) if error else None
    return await conn.fetchrow(
        """
        UPDATE jobs
        SET status = $2, updated_at = $3, completed_at = COALESCE($4, completed_at),
            error = COALESCE($5::jsonb, error), shipment_id = COALESCE($6, shipment_id)
        WHERE id = $1
        RETURNING *
        """,
        job_id,
        status,
        now,
        completed_at,
        error_json,
        shipment_id,
    )


async def list_by_account(
    conn: asyncpg.Connection,
    account_id: UUID,
    *,
    status: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> list[asyncpg.Record]:
    """List jobs for an account with optional status filter and cursor pagination."""
    if status:
        if cursor:
            return await conn.fetch(
                """
                SELECT * FROM jobs
                WHERE account_id = $1 AND status = $2 AND created_at < $3
                ORDER BY created_at DESC LIMIT $4
                """,
                account_id,
                status,
                cursor,
                limit,
            )
        return await conn.fetch(
            """
            SELECT * FROM jobs
            WHERE account_id = $1 AND status = $2
            ORDER BY created_at DESC LIMIT $3
            """,
            account_id,
            status,
            limit,
        )
    if cursor:
        return await conn.fetch(
            """
            SELECT * FROM jobs
            WHERE account_id = $1 AND created_at < $2
            ORDER BY created_at DESC LIMIT $3
            """,
            account_id,
            cursor,
            limit,
        )
    return await conn.fetch(
        """
        SELECT * FROM jobs
        WHERE account_id = $1
        ORDER BY created_at DESC LIMIT $2
        """,
        account_id,
        limit,
    )


async def delete(conn: asyncpg.Connection, job_id: UUID) -> bool:
    """Delete a job. Returns True if a row was deleted."""
    result = await conn.execute(
        "DELETE FROM jobs WHERE id = $1",
        job_id,
    )
    return result == "DELETE 1"
