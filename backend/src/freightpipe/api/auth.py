"""Authentication — supports both X-Api-Key and JWT Bearer token."""
from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from freightpipe.api.auth_jwt import decode_access_token
from freightpipe.db.connection import get_pool
from freightpipe.db.repos import api_keys as api_keys_repo

_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_account_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    api_key: str | None = Depends(_api_key_header),
) -> UUID:
    """Validate JWT Bearer token or X-Api-Key header and return the associated account_id.

    JWT is tried first; if absent or invalid, falls back to API key.
    Raises 401 if neither method succeeds.
    """
    # --- Try JWT first ---
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            account_id_str = payload.get("account_id")
            if account_id_str:
                return UUID(account_id_str)
        except (ValueError, KeyError):
            pass  # fall through to API key

    # --- Fall back to API key ---
    if api_key:
        key_hash = _hash_key(api_key)
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await api_keys_repo.get_by_hash(conn, key_hash)

        if row is not None:
            return row["account_id"]

    raise HTTPException(
        status_code=401,
        detail={
            "error": {
                "code": "unauthorized",
                "message": "Missing or invalid credentials. Provide Authorization: Bearer <jwt> or X-Api-Key header.",
                "request_id": _request_id(request),
            }
        },
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")
