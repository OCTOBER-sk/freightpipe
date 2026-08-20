"""Accounts repository — CRUD for the accounts table."""
from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg


async def create(
    conn: asyncpg.Connection,
    *,
    name: str,
    llm_byok_keys: dict | None = None,
) -> asyncpg.Record:
    """Create a new account. Returns the inserted row."""
    account_id = uuid4()
    now = datetime.utcnow()
    byok = json.dumps(llm_byok_keys or {})
    return await conn.fetchrow(
        """
        INSERT INTO accounts (id, name, created_at, llm_byok_keys)
        VALUES ($1, $2, $3, $4::jsonb)
        RETURNING *
        """,
        account_id,
        name,
        now,
        byok,
    )


async def get_by_id(conn: asyncpg.Connection, account_id: UUID) -> asyncpg.Record | None:
    """Fetch an account by ID."""
    return await conn.fetchrow(
        "SELECT * FROM accounts WHERE id = $1",
        account_id,
    )


async def update_byok_keys(
    conn: asyncpg.Connection,
    account_id: UUID,
    llm_byok_keys: dict,
) -> asyncpg.Record | None:
    """Update the BYOK keys for an account."""
    return await conn.fetchrow(
        """
        UPDATE accounts SET llm_byok_keys = $2::jsonb
        WHERE id = $1
        RETURNING *
        """,
        account_id,
        json.dumps(llm_byok_keys),
    )


async def delete(conn: asyncpg.Connection, account_id: UUID) -> bool:
    """Delete an account. Returns True if a row was deleted."""
    result = await conn.execute(
        "DELETE FROM accounts WHERE id = $1",
        account_id,
    )
    return result == "DELETE 1"


async def list_all(
    conn: asyncpg.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[asyncpg.Record]:
    """List all accounts with pagination."""
    return await conn.fetch(
        "SELECT * FROM accounts ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit,
        offset,
    )
