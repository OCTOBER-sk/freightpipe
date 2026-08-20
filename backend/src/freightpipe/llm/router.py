"""Provider-agnostic LLM router — BACKEND.md §2.1.

Key pool, round-robin, 429 backoff, fallback chain:
OpenRouter free -> Gemini Flash -> Groq -> BYOK
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import os
import random

@dataclass
class KeyState:
    key: str
    provider: str
    requests_today: int = 0
    requests_this_minute: int = 0
    last_used_at: datetime | None = None
    cooldown_until: datetime | None = None

    @property
    def is_healthy(self) -> bool:
        now = datetime.utcnow()
        if self.cooldown_until and now < self.cooldown_until:
            return False
        return True

@dataclass
class LLMRouter:
    """Routes LLM calls across providers with fallback and caching."""
    keys: list[KeyState] = field(default_factory=list)
    fallback_chain: list[str] = field(default_factory=lambda: ["openrouter", "gemini", "groq", "byok"])

    def _get_healthy_key(self, provider: str) -> KeyState | None:
        candidates = [k for k in self.keys if k.provider == provider and k.is_healthy]
        if not candidates:
            return None
        return min(candidates, key=lambda k: k.requests_today)

    async def complete(self, task_type: str, prompt: str, schema: dict | None = None,
                       requires_vision: bool = False) -> dict:
        """Route an LLM completion request through the fallback chain."""
        # TODO: Implement actual provider calls
        raise NotImplementedError("LLM router not yet implemented")

    @staticmethod
    def cache_key(prompt_template_id: str, text_hash: str, schema_version: str) -> str:
        raw = f"{prompt_template_id}:{text_hash}:{schema_version}"
        return hashlib.sha256(raw.encode()).hexdigest()
