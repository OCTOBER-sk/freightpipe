"""LLM cache repository — CRUD for the llm_cache table."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import asyncpg

DEFAULT_TTL_DAYS = 30


async def get(
    conn: asyncpg.Connection,
    cache_key: str,
) -> asyncpg.Record | None:
    """Fetch a cache entry if it exists and hasn't expired."""
    now = datetime.utcnow()
    return await conn.fetchrow(
        """
        SELECT * FROM llm_cache
        WHERE cache_key = $1 AND ttl_expires_at > $2
        """,
        cache_key,
        now,
    )


async def set(
    conn: asyncpg.Connection,
    *,
    cache_key: str,
    provider: str,
    model: str,
    response_json: dict,
    ttl_days: int = DEFAULT_TTL_DAYS,
) -> asyncpg.Record:
    """Insert or update a cache entry. Returns the row."""
    now = datetime.utcnow()
    ttl_expires = now + timedelta(days=ttl_days)
    return await conn.fetchrow(
        """
        INSERT INTO llm_cache (cache_key, provider, model, response_json, created_at, ttl_expires_at)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6)
        ON CONFLICT (cache_key) DO UPDATE
        SET provider = EXCLUDED.provider, model = EXCLUDED.model,
            response_json = EXCLUDED.response_json, created_at = EXCLUDED.created_at,
            ttl_expires_at = EXCLUDED.ttl_expires_at
        RETURNING *
        """,
        cache_key,
        provider,
        model,
        json.dumps(response_json),
        now,
        ttl_expires,
    )


async def cleanup_expired(conn: asyncpg.Connection) -> str:
    """Delete all expired cache entries (alias for delete_expired)."""
    return await delete_expired(conn)


async def delete_expired(conn: asyncpg.Connection) -> str:
    """Delete all expired cache entries."""
    now = datetime.utcnow()
    return await conn.execute(
        "DELETE FROM llm_cache WHERE ttl_expires_at <= $1",
        now,
    )


async def delete_by_key(conn: asyncpg.Connection, cache_key: str) -> bool:
    """Delete a specific cache entry."""
    result = await conn.execute(
        "DELETE FROM llm_cache WHERE cache_key = $1",
        cache_key,
    )
    return result == "DELETE 1"


async def count(conn: asyncpg.Connection) -> int:
    """Count total non-expired cache entries."""
    now = datetime.utcnow()
    row = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM llm_cache WHERE ttl_expires_at > $1",
        now,
    )
    return row["cnt"]
