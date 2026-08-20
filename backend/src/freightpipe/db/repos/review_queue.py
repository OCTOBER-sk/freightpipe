"""Review queue repository — CRUD for the review_queue table."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import asyncpg


async def create(
    conn: asyncpg.Connection,
    *,
    job_id: UUID,
    reason: str,
    state: str = "pending",
    assigned_to: str | None = None,
) -> asyncpg.Record:
    """Create a new review queue item. Returns the inserted row."""
    item_id = uuid4()
    now = datetime.utcnow()
    return await conn.fetchrow(
        """
        INSERT INTO review_queue (id, job_id, reason, state, assigned_to, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        item_id,
        job_id,
        reason,
        state,
        assigned_to,
        now,
    )


async def get_by_id(conn: asyncpg.Connection, item_id: UUID) -> asyncpg.Record | None:
    """Fetch a review queue item by ID."""
    return await conn.fetchrow(
        "SELECT * FROM review_queue WHERE id = $1",
        item_id,
    )


async def list_by_job(conn: asyncpg.Connection, job_id: UUID) -> list[asyncpg.Record]:
    """List all review items for a job."""
    return await conn.fetch(
        """
        SELECT * FROM review_queue
        WHERE job_id = $1
        ORDER BY created_at ASC
        """,
        job_id,
    )


async def list_by_state(
    conn: asyncpg.Connection,
    *,
    state: str = "pending",
    limit: int = 50,
    cursor: str | None = None,
) -> list[asyncpg.Record]:
    """List review items by state with cursor pagination."""
    if cursor:
        return await conn.fetch(
            """
            SELECT * FROM review_queue
            WHERE state = $1 AND created_at < $2
            ORDER BY created_at DESC LIMIT $3
            """,
            state,
            cursor,
            limit,
        )
    return await conn.fetch(
        """
        SELECT * FROM review_queue
        WHERE state = $1
        ORDER BY created_at DESC LIMIT $2
        """,
        state,
        limit,
    )


async def update_state(
    conn: asyncpg.Connection,
    item_id: UUID,
    *,
    state: str,
    assigned_to: str | None = None,
    resolution_notes: str | None = None,
) -> asyncpg.Record | None:
    """Update review item state. Returns updated row."""
    now = datetime.utcnow()
    resolved_at = now if state in ("resolved", "escalated") else None
    return await conn.fetchrow(
        """
        UPDATE review_queue
        SET state = $2, assigned_to = COALESCE($3, assigned_to),
            resolution_notes = COALESCE($4, resolution_notes),
            resolved_at = COALESCE($5, resolved_at)
        WHERE id = $1
        RETURNING *
        """,
        item_id,
        state,
        assigned_to,
        resolution_notes,
        resolved_at,
    )


async def delete(conn: asyncpg.Connection, item_id: UUID) -> bool:
    """Delete a review queue item."""
    result = await conn.execute(
        "DELETE FROM review_queue WHERE id = $1",
        item_id,
    )
    return result == "DELETE 1"
