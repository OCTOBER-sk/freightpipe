"""Provider-agnostic LLM router — BACKEND.md §2.1.

Key pool, round-robin, 429 backoff, fallback chain:
OpenRouter free -> Gemini Flash -> Groq -> BYOK

Response cache (sha256 key, Postgres llm_cache, 30-day TTL).
Daily budget tracker (90% soft ceiling).
Metering log (provider_usage_log table).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

class Provider(str, Enum):
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    GROQ = "groq"
    BYOK = "byok"


# Default fallback chain for extraction tasks (BACKEND.md §2.1)
DEFAULT_FALLBACK_CHAIN: list[str] = [
    Provider.OPENROUTER,
    Provider.GEMINI,
    Provider.GROQ,
    Provider.BYOK,
]

# Provider-specific defaults
PROVIDER_MODELS: dict[str, str] = {
    Provider.OPENROUTER: "nvidia/nemotron-3-ultra-550b-a55b:free",
    Provider.GEMINI: "gemini-2.5-flash",
    Provider.GROQ: "openai/gpt-oss-20b",
    Provider.BYOK: "",  # user-supplied
}

PROVIDER_ENDPOINTS: dict[str, str] = {
    Provider.OPENROUTER: "https://openrouter.ai/api/v1/chat/completions",
    Provider.GEMINI: "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    Provider.GROQ: "https://api.groq.com/openai/v1/chat/completions",
}

# Default daily limits (free tier, from BACKEND.md §2.1)
PROVIDER_DAILY_LIMITS: dict[str, int] = {
    Provider.OPENROUTER: 50,
    Provider.GEMINI: 1500,
    Provider.GROQ: 14400,
    Provider.BYOK: 1_000_000,  # effectively unlimited
}

# Exponential backoff sequence for 429s: 30s, 60s, 120s, cap 10min
BACKOFF_SEQUENCE = [30, 60, 120, 300, 600]  # seconds; capped at 600 (10min)

# Budget soft ceiling (BACKEND.md §2.6)
BUDGET_SOFT_CEILING_PCT = int(os.environ.get("LLM_DAILY_BUDGET_SOFT_CEILING_PCT", "90"))


# ---------------------------------------------------------------------------
# Key state tracking
# ---------------------------------------------------------------------------

@dataclass
class KeyState:
    """Tracks health and usage for a single API key."""
    key: str
    provider: str
    model: str = ""
    requests_today: int = 0
    requests_this_minute: int = 0
    last_used_at: datetime | None = None
    cooldown_until: datetime | None = None
    backoff_index: int = 0  # index into BACKOFF_SEQUENCE

    @property
    def is_healthy(self) -> bool:
        """A key is healthy if not in cooldown."""
        now = datetime.utcnow()
        if self.cooldown_until and now < self.cooldown_until:
            return False
        return True

    def mark_rate_limited(self) -> None:
        """Apply exponential backoff on 429."""
        delay = BACKOFF_SEQUENCE[min(self.backoff_index, len(BACKOFF_SEQUENCE) - 1)]
        self.cooldown_until = datetime.utcnow() + timedelta(seconds=delay)
        self.backoff_index = min(self.backoff_index + 1, len(BACKOFF_SEQUENCE) - 1)
        logger.warning(
            "Key for %s rate-limited, backing off %ds (until %s)",
            self.provider, delay, self.cooldown_until,
        )

    def mark_used(self) -> None:
        """Record a successful use."""
        self.requests_today += 1
        self.requests_this_minute += 1
        self.last_used_at = datetime.utcnow()
        # Reset backoff on success
        self.backoff_index = 0
        self.cooldown_until = None


# ---------------------------------------------------------------------------
# LLM Router
# ---------------------------------------------------------------------------

@dataclass
class LLMRouter:
    """Routes LLM calls across providers with fallback, caching, and metering.

    Usage:
        router = LLMRouter.from_env()
        result = await router.complete("extraction", prompt, schema={...})
    """
    keys: list[KeyState] = field(default_factory=list)
    fallback_chain: list[str] = field(default_factory=lambda: list(DEFAULT_FALLBACK_CHAIN))
    _http_client: httpx.AsyncClient | None = field(default=None, repr=False)
    _db_pool: object | None = field(default=None, repr=False)  # asyncpg.Pool

    # ----- Factory -----

    @classmethod
    def from_env(cls, db_pool: object | None = None) -> LLMRouter:
        """Build a router from environment variables (comma-separated key pools)."""
        router = cls()
        router._db_pool = db_pool

        # Load keys per provider
        for provider, env_var in [
            (Provider.OPENROUTER, "OPENROUTER_API_KEYS"),
            (Provider.GEMINI, "GEMINI_API_KEYS"),
            (Provider.GROQ, "GROQ_API_KEYS"),
        ]:
            raw = os.environ.get(env_var, "")
            for k in raw.split(","):
                k = k.strip()
                if k:
                    router.keys.append(KeyState(
                        key=k,
                        provider=provider,
                        model=PROVIDER_MODELS[provider],
                    ))

        # BYOK keys come from the account (passed at call time), not env
        return router

    # ----- HTTP client -----

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    # ----- Key selection -----

    def _get_healthy_keys(self, provider: str) -> list[KeyState]:
        """Get all healthy keys for a provider, sorted by least-recently-used."""
        candidates = [
            k for k in self.keys
            if k.provider == provider and k.is_healthy
        ]
        candidates.sort(key=lambda k: (k.requests_today, k.last_used_at or datetime.min))
        return candidates

    def _check_budget(self, provider: str) -> bool:
        """Check if provider is within the daily budget soft ceiling."""
        provider_keys = [k for k in self.keys if k.provider == provider]
        total_today = sum(k.requests_today for k in provider_keys)
        limit = PROVIDER_DAILY_LIMITS.get(provider, 0)
        threshold = int(limit * BUDGET_SOFT_CEILING_PCT / 100)
        return total_today < threshold

    # ----- Cache -----

    @staticmethod
    def cache_key(prompt_template_id: str, text_hash: str, schema_version: str) -> str:
        """Compute sha256 cache key per BACKEND.md §2.6."""
        raw = f"{prompt_template_id}:{text_hash}:{schema_version}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _get_cache(self, key: str) -> dict | None:
        """Check llm_cache table for a hit."""
        if not self._db_pool:
            return None
        from freightpipe.db.repos import llm_cache
        async with self._db_pool.acquire() as conn:  # type: ignore[union-attr]
            row = await llm_cache.get(conn, key)
            if row:
                return dict(row["response_json"])
        return None

    async def _set_cache(
        self, key: str, provider: str, model: str, response: dict
    ) -> None:
        """Write to llm_cache table."""
        if not self._db_pool:
            return
        from freightpipe.db.repos import llm_cache
        async with self._db_pool.acquire() as conn:  # type: ignore[union-attr]
            await llm_cache.set(
                conn,
                cache_key=key,
                provider=provider,
                model=model,
                response_json=response,
            )

    # ----- Metering -----

    async def _log_usage(self, provider: str, model: str, is_cache_hit: bool = False) -> None:
        """Increment provider_usage_log."""
        if not self._db_pool:
            return
        from freightpipe.db.repos import provider_usage_log
        async with self._db_pool.acquire() as conn:  # type: ignore[union-attr]
            await provider_usage_log.increment(
                conn,
                provider=provider,
                model=model,
                is_cache_hit=is_cache_hit,
            )

    # ----- Provider calls -----

    async def _call_openrouter(self, key: KeyState, prompt: str, schema: dict | None) -> dict:
        """Call OpenRouter chat completions API."""
        messages = [{"role": "user", "content": prompt}]
        body: dict = {
            "model": key.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if schema:
            body["response_format"] = {"type": "json_object"}

        resp = await self.http.post(
            PROVIDER_ENDPOINTS[Provider.OPENROUTER],
            headers={
                "Authorization": f"Bearer {key.key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

        if resp.status_code == 429:
            raise RateLimitError(provider=Provider.OPENROUTER, status_code=429)

        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"text": content, "model": key.model, "provider": Provider.OPENROUTER}

    async def _call_gemini(self, key: KeyState, prompt: str, schema: dict | None) -> dict:
        """Call Gemini API (Google AI Studio)."""
        model = key.model or PROVIDER_MODELS[Provider.GEMINI]
        url = PROVIDER_ENDPOINTS[Provider.GEMINI].format(model=model)
        body: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }
        if schema:
            body["generationConfig"]["responseMimeType"] = "application/json"

        resp = await self.http.post(
            f"{url}?key={key.key}",
            headers={"Content-Type": "application/json"},
            json=body,
        )

        if resp.status_code == 429:
            raise RateLimitError(provider=Provider.GEMINI, status_code=429)

        resp.raise_for_status()
        data = resp.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"text": content, "model": model, "provider": Provider.GEMINI}

    async def _call_groq(self, key: KeyState, prompt: str, schema: dict | None) -> dict:
        """Call Groq chat completions API."""
        messages = [{"role": "user", "content": prompt}]
        body: dict = {
            "model": key.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if schema:
            body["response_format"] = {"type": "json_object"}

        resp = await self.http.post(
            PROVIDER_ENDPOINTS[Provider.GROQ],
            headers={
                "Authorization": f"Bearer {key.key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

        if resp.status_code == 429:
            raise RateLimitError(provider=Provider.GROQ, status_code=429)

        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"text": content, "model": key.model, "provider": Provider.GROQ}

    async def _call_byok(
        self, key: KeyState, prompt: str, schema: dict | None, byok_config: dict | None = None
    ) -> dict:
        """Call a BYOK-configured provider. Expects byok_config with endpoint/model/key."""
        if not byok_config:
            raise ValueError("BYOK config required for byok provider")

        endpoint = byok_config.get("endpoint", "")
        model = byok_config.get("model", "")
        api_key = byok_config.get("api_key", key.key)

        messages = [{"role": "user", "content": prompt}]
        body: dict = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
        }
        if schema:
            body["response_format"] = {"type": "json_object"}

        resp = await self.http.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

        if resp.status_code == 429:
            raise RateLimitError(provider=Provider.BYOK, status_code=429)

        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"text": content, "model": model, "provider": Provider.BYOK}

    async def _dispatch(
        self,
        key: KeyState,
        prompt: str,
        schema: dict | None,
        byok_config: dict | None = None,
    ) -> dict:
        """Dispatch to the correct provider call based on key.provider."""
        provider = key.provider
        if provider == Provider.OPENROUTER:
            return await self._call_openrouter(key, prompt, schema)
        elif provider == Provider.GEMINI:
            return await self._call_gemini(key, prompt, schema)
        elif provider == Provider.GROQ:
            return await self._call_groq(key, prompt, schema)
        elif provider == Provider.BYOK:
            return await self._call_byok(key, prompt, schema, byok_config)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    # ----- Main entry point -----

    async def complete(
        self,
        task_type: str,
        prompt: str,
        schema: dict | None = None,
        requires_vision: bool = False,
        prompt_template_id: str = "",
        text_hash: str = "",
        schema_version: str = "1",
        byok_config: dict | None = None,
    ) -> dict:
        """Route an LLM completion request through the fallback chain.

        Args:
            task_type: e.g. "extraction", "classification"
            prompt: the full prompt text
            schema: optional JSON schema for structured output
            requires_vision: if True, prefer Gemini (vision-capable)
            prompt_template_id: for cache key computation
            text_hash: for cache key computation
            schema_version: for cache key computation
            byok_config: optional BYOK provider config

        Returns:
            dict with keys: text, model, provider, cached (bool)

        Raises:
            LLMCapacityExhausted: if all providers fail
        """
        # 1. Check cache
        if prompt_template_id and text_hash:
            ck = self.cache_key(prompt_template_id, text_hash, schema_version)
            cached = await self._get_cache(ck)
            if cached:
                await self._log_usage(
                    cached.get("provider", "unknown"),
                    cached.get("model", "unknown"),
                    is_cache_hit=True,
                )
                return {**cached, "cached": True}

        # 2. Build provider order (vision → Gemini first)
        chain = list(self.fallback_chain)
        if requires_vision and Provider.GEMINI in chain:
            chain.remove(Provider.GEMINI)
            chain.insert(0, Provider.GEMINI)

        # 3. Walk the fallback chain
        last_error: Exception | None = None
        for provider in chain:
            # Budget check
            if not self._check_budget(provider):
                logger.info("Provider %s at budget ceiling, skipping", provider)
                continue

            healthy_keys = self._get_healthy_keys(provider)
            if not healthy_keys:
                logger.info("No healthy keys for provider %s, skipping", provider)
                continue

            # Try each healthy key for this provider
            for key in healthy_keys:
                try:
                    result = await self._dispatch(key, prompt, schema, byok_config)
                    key.mark_used()

                    # Cache the result
                    if prompt_template_id and text_hash:
                        ck = self.cache_key(prompt_template_id, text_hash, schema_version)
                        await self._set_cache(
                            ck,
                            result["provider"],
                            result["model"],
                            {"text": result["text"], "model": result["model"], "provider": result["provider"]},
                        )

                    # Log usage
                    await self._log_usage(result["provider"], result["model"])

                    return {**result, "cached": False}

                except RateLimitError:
                    key.mark_rate_limited()
                    last_error = LLMCapacityExhausted(
                        f"Rate limited on {provider}, trying next"
                    )
                    continue
                except Exception as e:
                    logger.error("Error calling %s: %s", provider, e)
                    last_error = e
                    continue

        # 4. All providers exhausted
        raise LLMCapacityExhausted(
            f"All providers exhausted for task '{task_type}'. "
            f"Last error: {last_error}"
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RateLimitError(Exception):
    """Raised when a provider returns 429."""
    def __init__(self, provider: str, status_code: int = 429):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"Rate limited by {provider} (HTTP {status_code})")


class LLMCapacityExhausted(Exception):
    """Raised when all providers in the fallback chain are exhausted.

    Per BACKEND.md §2.1: job dropped into review queue as NEEDS_LLM_CAPACITY.
    """
    pass
