"""API key authentication — X-Api-Key header validation, account-scoped access."""
from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from freightpipe.db.connection import get_pool
from freightpipe.db.repos import api_keys as api_keys_repo

_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_account_id(request: Request, api_key: str | None = Depends(_api_key_header)) -> UUID:
    """Validate X-Api-Key header and return the associated account_id.

    Raises 401 if the key is missing, invalid, or revoked.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "unauthorized",
                    "message": "Missing or invalid API key.",
                    "request_id": _request_id(request),
                }
            },
        )

    key_hash = _hash_key(api_key)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await api_keys_repo.get_by_hash(conn, key_hash)

    if row is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "unauthorized",
                    "message": "Missing or invalid API key.",
                    "request_id": _request_id(request),
                }
            },
        )

    return row["account_id"]


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")
