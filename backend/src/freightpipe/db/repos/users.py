"""Users repository — CRUD for the users table."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg


async def create(
    conn: asyncpg.Connection,
    *,
    email: str,
    phone: str | None,
    company_name: str,
    password_hash: str,
) -> asyncpg.Record:
    user_id = uuid4()
    now = datetime.now(UTC)
    return await conn.fetchrow(
        """
        INSERT INTO users (id, email, phone, company_name, password_hash, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        user_id,
        email,
        phone,
        company_name,
        password_hash,
        now,
        now,
    )


async def get_by_id(conn: asyncpg.Connection, user_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow(
        "SELECT * FROM users WHERE id = $1",
        user_id,
    )


async def get_by_email(conn: asyncpg.Connection, email: str) -> asyncpg.Record | None:
    return await conn.fetchrow(
        "SELECT * FROM users WHERE email = $1",
        email,
    )


async def update_profile(
    conn: asyncpg.Connection,
    user_id: UUID,
    *,
    phone: str | None = None,
    company_name: str | None = None,
) -> asyncpg.Record | None:
    now = datetime.now(UTC)
    return await conn.fetchrow(
        """
        UPDATE users
        SET phone = COALESCE($2, phone),
            company_name = COALESCE($3, company_name),
            updated_at = $4
        WHERE id = $1
        RETURNING *
        """,
        user_id,
        phone,
        company_name,
        now,
    )
