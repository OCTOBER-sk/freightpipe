"""Neon Postgres connection pool via asyncpg."""
import os
import asyncpg

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ["NEON_DATABASE_URL"]
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
