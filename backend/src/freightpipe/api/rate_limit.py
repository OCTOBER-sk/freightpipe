"""Per-account rate limiting — 60 submissions/hour default (BACKEND.md §4.4)."""
from __future__ import annotations

import time
from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException, Request

_DEFAULT_LIMIT = 60
_WINDOW_SECONDS = 3600  # 1 hour

# In-memory sliding window: account_id -> list of submission timestamps
_windows: dict[UUID, list[float]] = defaultdict(list)


def check_rate_limit(account_id: UUID, request: Request, limit: int = _DEFAULT_LIMIT) -> None:
    """Raise 429 if the account exceeds the rate limit.

    Uses an in-memory sliding window counter. In production this would be
    backed by Cloudflare Workers KV counters (per BACKEND.md §4.4).
    """
    now = time.time()
    window = _windows[account_id]

    # Prune timestamps outside the window
    cutoff = now - _WINDOW_SECONDS
    _windows[account_id] = [ts for ts in window if ts > cutoff]
    window = _windows[account_id]

    if len(window) >= limit:
        retry_after = int(window[0] + _WINDOW_SECONDS - now) + 1
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "rate_limited",
                    "message": f"Rate limit exceeded. Max {limit} submissions per hour.",
                    "request_id": _request_id(request),
                }
            },
            headers={"Retry-After": str(retry_after)},
        )

    window.append(now)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")
