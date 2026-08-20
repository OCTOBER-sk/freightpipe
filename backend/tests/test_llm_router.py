"""Tests for LLM router — key pool, round-robin, backoff, cache, budget, metering."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from freightpipe.llm.router import (
    BACKOFF_SEQUENCE,
    BUDGET_SOFT_CEILING_PCT,
    DEFAULT_FALLBACK_CHAIN,
    PROVIDER_DAILY_LIMITS,
    KeyState,
    LLMCapacityExhausted,
    LLMRouter,
    Provider,
    RateLimitError,
)


# ---------------------------------------------------------------------------
# KeyState
# ---------------------------------------------------------------------------

class TestKeyState:
    def test_is_healthy_default(self):
        key = KeyState(key="test", provider=Provider.OPENROUTER)
        assert key.is_healthy is True

    def test_is_healthy_in_cooldown(self):
        key = KeyState(key="test", provider=Provider.OPENROUTER)
        key.cooldown_until = datetime.utcnow() + timedelta(seconds=60)
        assert key.is_healthy is False

    def test_is_healthy_cooldown_expired(self):
        key = KeyState(key="test", provider=Provider.OPENROUTER)
        key.cooldown_until = datetime.utcnow() - timedelta(seconds=10)
        assert key.is_healthy is True

    def test_mark_rate_limited(self):
        key = KeyState(key="test", provider=Provider.OPENROUTER)
        key.mark_rate_limited()
        assert key.cooldown_until is not None
        assert key.is_healthy is False
        assert key.backoff_index == 1

    def test_mark_rate_limited_exponential_backoff(self):
        key = KeyState(key="test", provider=Provider.OPENROUTER)
        key.mark_rate_limited()
        delay1 = (key.cooldown_until - datetime.utcnow()).total_seconds()
        assert 25 <= delay1 <= 35

        key.cooldown_until = datetime.utcnow() - timedelta(seconds=1)
        key.mark_rate_limited()
        delay2 = (key.cooldown_until - datetime.utcnow()).total_seconds()
        assert 55 <= delay2 <= 65

    def test_mark_rate_limited_capped_at_10min(self):
        key = KeyState(key="test", provider=Provider.OPENROUTER)
        key.backoff_index = 100
        key.mark_rate_limited()
        delay = (key.cooldown_until - datetime.utcnow()).total_seconds()
        assert delay <= BACKOFF_SEQUENCE[-1] + 5

    def test_mark_used_resets_backoff(self):
        key = KeyState(key="test", provider=Provider.OPENROUTER)
        key.mark_rate_limited()
        assert key.backoff_index == 1
        key.mark_used()
        assert key.backoff_index == 0
        assert key.cooldown_until is None
        assert key.requests_today == 1


# ---------------------------------------------------------------------------
# LLMRouter — key loading
# ---------------------------------------------------------------------------

class TestLLMRouterInit:
    def test_from_env_loads_keys(self):
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEYS": "or_key1,or_key2",
            "GEMINI_API_KEYS": "gem_key1",
            "GROQ_API_KEYS": "groq_key1",
        }):
            router = LLMRouter.from_env()
        assert len(router.keys) == 4
        providers = {k.provider for k in router.keys}
        assert Provider.OPENROUTER in providers
        assert Provider.GEMINI in providers
        assert Provider.GROQ in providers

    def test_from_env_empty_keys(self):
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEYS": "",
            "GEMINI_API_KEYS": "",
            "GROQ_API_KEYS": "",
        }, clear=False):
            router = LLMRouter.from_env()
        assert len(router.keys) == 0

    def test_from_env_strips_whitespace(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEYS": " key1 , key2 "}):
            router = LLMRouter.from_env()
        assert router.keys[0].key == "key1"
        assert router.keys[1].key == "key2"

    def test_from_env_skips_empty(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEYS", "key1,,key2,")
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        monkeypatch.delenv("GROQ_API_KEYS", raising=False)
        router = LLMRouter.from_env()
        assert len(router.keys) == 2

    def test_default_fallback_chain(self):
        router = LLMRouter()
        assert router.fallback_chain == [
            Provider.OPENROUTER,
            Provider.GEMINI,
            Provider.GROQ,
            Provider.BYOK,
        ]


# ---------------------------------------------------------------------------
# Key selection
# ---------------------------------------------------------------------------

class TestKeySelection:
    def test_get_healthy_keys_filters_unhealthy(self):
        router = LLMRouter()
        healthy = KeyState(key="h", provider=Provider.OPENROUTER)
        unhealthy = KeyState(key="u", provider=Provider.OPENROUTER)
        unhealthy.cooldown_until = datetime.utcnow() + timedelta(hours=1)
        router.keys = [healthy, unhealthy]
        result = router._get_healthy_keys(Provider.OPENROUTER)
        assert len(result) == 1
        assert result[0].key == "h"

    def test_get_healthy_keys_sorted_by_usage(self):
        router = LLMRouter()
        k1 = KeyState(key="k1", provider=Provider.OPENROUTER, requests_today=10)
        k2 = KeyState(key="k2", provider=Provider.OPENROUTER, requests_today=5)
        k3 = KeyState(key="k3", provider=Provider.OPENROUTER, requests_today=15)
        router.keys = [k1, k2, k3]
        result = router._get_healthy_keys(Provider.OPENROUTER)
        assert result[0].key == "k2"
        assert result[1].key == "k1"
        assert result[2].key == "k3"

    def test_get_healthy_keys_empty_provider(self):
        router = LLMRouter()
        router.keys = [KeyState(key="k", provider=Provider.GROQ)]
        result = router._get_healthy_keys(Provider.OPENROUTER)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class TestBudgetCheck:
    def test_budget_under_ceiling(self):
        router = LLMRouter()
        router.keys = [KeyState(key="k", provider=Provider.OPENROUTER, requests_today=10)]
        assert router._check_budget(Provider.OPENROUTER) is True

    def test_budget_at_ceiling(self):
        router = LLMRouter()
        limit = PROVIDER_DAILY_LIMITS[Provider.OPENROUTER]
        threshold = int(limit * BUDGET_SOFT_CEILING_PCT / 100)
        router.keys = [KeyState(key="k", provider=Provider.OPENROUTER, requests_today=threshold)]
        assert router._check_budget(Provider.OPENROUTER) is False

    def test_budget_over_ceiling(self):
        router = LLMRouter()
        router.keys = [KeyState(key="k", provider=Provider.OPENROUTER, requests_today=999999)]
        assert router._check_budget(Provider.OPENROUTER) is False


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_cache_key_deterministic(self):
        k1 = LLMRouter.cache_key("template1", "hash1", "v1")
        k2 = LLMRouter.cache_key("template1", "hash1", "v1")
        assert k1 == k2

    def test_cache_key_different_inputs(self):
        k1 = LLMRouter.cache_key("template1", "hash1", "v1")
        k2 = LLMRouter.cache_key("template2", "hash1", "v1")
        assert k1 != k2

    def test_cache_key_is_sha256(self):
        k = LLMRouter.cache_key("t", "h", "v")
        raw = "t:h:v"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert k == expected


# ---------------------------------------------------------------------------
# Complete — fallback chain
# ---------------------------------------------------------------------------

class TestComplete:
    @pytest.mark.asyncio
    async def test_returns_cached(self):
        router = LLMRouter()
        cached = {"text": "cached", "model": "m", "provider": "p"}
        with patch.object(router, "_get_cache", return_value=cached), \
             patch.object(router, "_log_usage"):
            result = await router.complete(
                "test", "prompt", prompt_template_id="t1", text_hash="h1",
            )
            assert result["cached"] is True
            assert result["text"] == "cached"

    @pytest.mark.asyncio
    async def test_raises_when_all_exhausted(self):
        router = LLMRouter()
        router.keys = []
        with pytest.raises(LLMCapacityExhausted):
            await router.complete("test", "prompt")

    @pytest.mark.asyncio
    async def test_skips_over_budget(self):
        router = LLMRouter()
        limit = PROVIDER_DAILY_LIMITS[Provider.OPENROUTER]
        router.keys = [
            KeyState(key="or_key", provider=Provider.OPENROUTER, requests_today=limit),
        ]
        with pytest.raises(LLMCapacityExhausted):
            await router.complete("test", "prompt")

    @pytest.mark.asyncio
    async def test_falls_through_on_429(self):
        router = LLMRouter()
        k_or = KeyState(key="or_key", provider=Provider.OPENROUTER)
        k_groq = KeyState(key="groq_key", provider=Provider.GROQ)
        router.keys = [k_or, k_groq]

        async def mock_dispatch(key, prompt, schema, byok_config=None):
            if key.provider == Provider.OPENROUTER:
                raise RateLimitError(provider=Provider.OPENROUTER)
            return {"text": "ok", "model": "llama", "provider": Provider.GROQ}

        router._dispatch = mock_dispatch
        router._db_pool = None

        result = await router.complete("test", "prompt")
        assert result["provider"] == Provider.GROQ
        assert k_or.is_healthy is False

    @pytest.mark.asyncio
    async def test_vision_prefers_gemini(self):
        router = LLMRouter()
        k_gem = KeyState(key="gem_key", provider=Provider.GEMINI)
        k_or = KeyState(key="or_key", provider=Provider.OPENROUTER)
        router.keys = [k_or, k_gem]

        dispatched = []

        async def mock_dispatch(key, prompt, schema, byok_config=None):
            dispatched.append(key.provider)
            return {"text": "ok", "model": "flash", "provider": key.provider}

        router._dispatch = mock_dispatch
        router._db_pool = None

        await router.complete("test", "prompt", requires_vision=True)
        assert dispatched[0] == Provider.GEMINI

    @pytest.mark.asyncio
    async def test_caches_result(self):
        router = LLMRouter()
        key = KeyState(key="test", provider=Provider.OPENROUTER, model="m")
        router.keys = [key]

        async def mock_dispatch(key, prompt, schema, byok_config=None):
            return {"text": "new result", "model": "m", "provider": Provider.OPENROUTER}

        router._dispatch = mock_dispatch
        router._db_pool = None

        with patch.object(router, "_get_cache", return_value=None), \
             patch.object(router, "_set_cache") as mock_set_cache, \
             patch.object(router, "_log_usage"):
            result = await router.complete(
                "test", "prompt", prompt_template_id="t1", text_hash="h1",
            )
            assert result["cached"] is False
            mock_set_cache.assert_called_once()


# ---------------------------------------------------------------------------
# RateLimitError / LLMCapacityExhausted
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_rate_limit_error(self):
        err = RateLimitError(provider=Provider.OPENROUTER, status_code=429)
        assert err.provider == Provider.OPENROUTER
        assert err.status_code == 429

    def test_llm_capacity_exhausted(self):
        err = LLMCapacityExhausted("all exhausted")
        assert "all exhausted" in str(err)
