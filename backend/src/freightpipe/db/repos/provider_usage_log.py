"""Provider usage log repository — CRUD for the provider_usage_log table."""
from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import asyncpg


async def increment(
    conn: asyncpg.Connection,
    *,
    provider: str,
    model: str,
    log_date: date | None = None,
    is_cache_hit: bool = False,
) -> asyncpg.Record:
    """Increment request_count (and optionally cache_hit_count) for a provider/model/date.

    Uses UPSERT so a single row per (provider, model, log_date) is maintained.
    """
    today = log_date or date.today()
    cache_inc = 1 if is_cache_hit else 0
    return await conn.fetchrow(
        """
        INSERT INTO provider_usage_log (id, provider, model, log_date, request_count, cache_hit_count)
        VALUES ($1, $2, $3, $4, 1, $5)
        ON CONFLICT (provider, model, log_date) DO UPDATE
        SET request_count = provider_usage_log.request_count + 1,
            cache_hit_count = provider_usage_log.cache_hit_count + $5
        RETURNING *
        """,
        uuid4(),
        provider,
        model,
        today,
        cache_inc,
    )


async def get_usage(
    conn: asyncpg.Connection,
    *,
    provider: str,
    model: str,
    log_date: date | None = None,
) -> asyncpg.Record | None:
    """Get usage for a specific provider/model/date."""
    today = log_date or date.today()
    return await conn.fetchrow(
        """
        SELECT * FROM provider_usage_log
        WHERE provider = $1 AND model = $2 AND log_date = $3
        """,
        provider,
        model,
        today,
    )


async def get_daily_totals(
    conn: asyncpg.Connection,
    log_date: date | None = None,
) -> list[asyncpg.Record]:
    """Get usage totals across all providers for a given date."""
    today = log_date or date.today()
    return await conn.fetch(
        """
        SELECT provider, model, request_count, cache_hit_count
        FROM provider_usage_log
        WHERE log_date = $1
        ORDER BY provider, model
        """,
        today,
    )


async def get_total_requests_today(
    conn: asyncpg.Connection,
    provider: str,
    log_date: date | None = None,
) -> int:
    """Get total requests for a provider across all models today."""
    today = log_date or date.today()
    row = await conn.fetchrow(
        """
        SELECT COALESCE(SUM(request_count), 0) as total
        FROM provider_usage_log
        WHERE provider = $1 AND log_date = $2
        """,
        provider,
        today,
    )
    return row["total"]


async def list_range(
    conn: asyncpg.Connection,
    *,
    start_date: date,
    end_date: date,
) -> list[asyncpg.Record]:
    """List usage logs for a date range."""
    return await conn.fetch(
        """
        SELECT * FROM provider_usage_log
        WHERE log_date BETWEEN $1 AND $2
        ORDER BY log_date DESC, provider, model
        """,
        start_date,
        end_date,
    )
