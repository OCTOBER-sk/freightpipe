"""API keys repository — CRUD for the api_keys table."""
from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg


def hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def create(
    conn: asyncpg.Connection,
    *,
    account_id: UUID,
    key_hash: str,
    label: str | None = None,
) -> asyncpg.Record:
    """Insert a new API key row. Returns the inserted row."""
    key_id = uuid4()
    now = datetime.utcnow()
    return await conn.fetchrow(
        """
        INSERT INTO api_keys (id, account_id, key_hash, label, created_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        key_id,
        account_id,
        key_hash,
        label,
        now,
    )


async def get_by_id(conn: asyncpg.Connection, key_id: UUID) -> asyncpg.Record | None:
    """Fetch an API key by ID."""
    return await conn.fetchrow(
        "SELECT * FROM api_keys WHERE id = $1",
        key_id,
    )


async def get_by_hash(conn: asyncpg.Connection, key_hash: str) -> asyncpg.Record | None:
    """Fetch an API key by its hash (used during auth)."""
    return await conn.fetchrow(
        "SELECT * FROM api_keys WHERE key_hash = $1 AND revoked_at IS NULL",
        key_hash,
    )


async def list_by_account(
    conn: asyncpg.Connection,
    account_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[asyncpg.Record]:
    """List all API keys for an account."""
    return await conn.fetch(
        """
        SELECT * FROM api_keys
        WHERE account_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        account_id,
        limit,
        offset,
    )


async def revoke(conn: asyncpg.Connection, key_id: UUID) -> asyncpg.Record | None:
    """Revoke an API key by setting revoked_at. Returns updated row."""
    now = datetime.utcnow()
    return await conn.fetchrow(
        """
        UPDATE api_keys SET revoked_at = $2
        WHERE id = $1 AND revoked_at IS NULL
        RETURNING *
        """,
        key_id,
        now,
    )


async def delete(conn: asyncpg.Connection, key_id: UUID) -> bool:
    """Hard-delete an API key. Returns True if a row was deleted."""
    result = await conn.execute(
        "DELETE FROM api_keys WHERE id = $1",
        key_id,
    )
    return result == "DELETE 1"
