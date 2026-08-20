"""Match results repository — CRUD for the match_results table."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import asyncpg


async def create(
    conn: asyncpg.Connection,
    *,
    shipment_id: UUID,
    line_item: str,
    rate_con_value: str | None = None,
    bol_pod_value: str | None = None,
    invoice_value: str | None = None,
    discrepancy_flag: str = "none",
    discrepancy_amount: float | None = None,
) -> asyncpg.Record:
    """Create a new match result. Returns the inserted row."""
    result_id = uuid4()
    now = datetime.utcnow()
    return await conn.fetchrow(
        """
        INSERT INTO match_results (id, shipment_id, line_item, rate_con_value,
                                   bol_pod_value, invoice_value, discrepancy_flag,
                                   discrepancy_amount, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """,
        result_id,
        shipment_id,
        line_item,
        rate_con_value,
        bol_pod_value,
        invoice_value,
        discrepancy_flag,
        discrepancy_amount,
        now,
    )


async def get_by_id(conn: asyncpg.Connection, result_id: UUID) -> asyncpg.Record | None:
    """Fetch a match result by ID."""
    return await conn.fetchrow(
        "SELECT * FROM match_results WHERE id = $1",
        result_id,
    )


async def list_by_shipment(
    conn: asyncpg.Connection,
    shipment_id: UUID,
) -> list[asyncpg.Record]:
    """List all match results for a shipment."""
    return await conn.fetch(
        """
        SELECT * FROM match_results
        WHERE shipment_id = $1
        ORDER BY line_item ASC
        """,
        shipment_id,
    )


async def update_discrepancy(
    conn: asyncpg.Connection,
    result_id: UUID,
    *,
    discrepancy_flag: str,
    discrepancy_amount: float | None = None,
) -> asyncpg.Record | None:
    """Update discrepancy info for a match result."""
    return await conn.fetchrow(
        """
        UPDATE match_results
        SET discrepancy_flag = $2, discrepancy_amount = $3
        WHERE id = $1
        RETURNING *
        """,
        result_id,
        discrepancy_flag,
        discrepancy_amount,
    )


async def delete_by_shipment(conn: asyncpg.Connection, shipment_id: UUID) -> str:
    """Delete all match results for a shipment."""
    return await conn.execute(
        "DELETE FROM match_results WHERE shipment_id = $1",
        shipment_id,
    )


async def delete(conn: asyncpg.Connection, result_id: UUID) -> bool:
    """Delete a single match result."""
    result = await conn.execute(
        "DELETE FROM match_results WHERE id = $1",
        result_id,
    )
    return result == "DELETE 1"
