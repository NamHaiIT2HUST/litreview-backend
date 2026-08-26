"""Credentials, kept separate from provider and model.

The three used to be one thing. ``effective_openai_api_key`` returned whichever
of four different providers' keys happened to be set, the base URL was inferred
from the key's prefix, and the model name was rewritten from that same prefix.
Pasting a new key could therefore change the endpoint and the model without
saying so, and a key whose prefix matched no known pattern silently produced an
empty base URL, sending a third-party credential to api.openai.com.

Here a credential is only a credential. It identifies nothing and selects
nothing. That separation is what makes rotating a spent key safe -- and it is
the same separation that lets an embedding index survive a key change, since the
identity of an index is (provider, model, dimension) and never the key.

Several keys per provider are supported, because running out of quota mid-task
is routine. Keys carry an alias so logs can say which one was used without ever
printing the key.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

# How long a key is set aside after the provider says it is over quota. Long
# enough that a retry storm cannot hammer the same exhausted key, short enough
# that a per-minute limit recovers on its own.
_QUOTA_COOLDOWN_SECONDS = 120.0


@dataclass
class Credential:
    provider: str
    alias: str
    key: str
    # Set when the provider reported quota exhaustion; the key is skipped until
    # then. A key rejected outright (401) is disabled for the process instead.
    unavailable_until: float = 0.0
    disabled_reason: str = ""

    @property
    def is_available(self) -> bool:
        if self.disabled_reason:
            return False
        return time.monotonic() >= self.unavailable_until

    def cool_down(self, seconds: float = _QUOTA_COOLDOWN_SECONDS) -> None:
        self.unavailable_until = time.monotonic() + seconds

    def disable(self, reason: str) -> None:
        self.disabled_reason = reason


@dataclass
class _ProviderPool:
    provider: str
    credentials: list[Credential] = field(default_factory=list)
    _cursor: int = 0

    def next_available(self) -> Credential | None:
        """Round-robin over the usable keys.

        Deliberately ordered rather than random. ``effective_gemini_api_key``
        called ``random.choice`` on every read, so two reads inside one request
        could authenticate as two different Google projects: cost could not be
        attributed and a failure could not be reproduced.
        """
        usable = [c for c in self.credentials if c.is_available]
        if not usable:
            return None
        credential = usable[self._cursor % len(usable)]
        self._cursor += 1
        return credential


# Environment variable names per provider, in priority order. The plural form
# holds several keys; the singular is the ordinary one-key case.
_PROVIDER_ENV_VARS: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEYS", "OPENAI_API_KEY"),
    "gemini": ("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "groq": ("GROQ_API_KEYS", "GROQ_API_KEY"),
    "deepseek": ("DEEPSEEK_API_KEYS", "DEEPSEEK_API_KEY"),
    "openrouter": ("OPENROUTER_API_KEYS", "OPENROUTER_API_KEY"),
    "xkiro": ("XKIRO_API_KEYS", "XKIRO_API_KEY"),
}


def _parse_keys(provider: str, raw: str) -> list[Credential]:
    """Parse ``alias:key,alias:key`` or a plain comma-separated list.

    Aliases exist so a log line can name the key that cost money without
    printing it.
    """
    credentials: list[Credential] = []
    for index, entry in enumerate(raw.split(",")):
        entry = entry.strip().strip('"').strip("'")
        if not entry:
            continue
        if ":" in entry and not entry.startswith(("sk-", "gsk_", "AIza")):
            alias, _, key = entry.partition(":")
            alias, key = alias.strip(), key.strip()
        else:
            alias, key = f"key{index + 1}", entry
        if key:
            credentials.append(Credential(provider=provider, alias=alias, key=key))
    return credentials


class CredentialStore:
    """Every configured key, grouped by provider, held for the process lifetime."""

    def __init__(self):
        self._pools: dict[str, _ProviderPool] = {}
        self.reload()

    def reload(self) -> None:
        self._pools = {}
        for provider, env_vars in _PROVIDER_ENV_VARS.items():
            pool = _ProviderPool(provider=provider)
            for env_var in env_vars:
                raw = os.getenv(env_var, "")
                if raw.strip():
                    pool.credentials.extend(_parse_keys(provider, raw))
                    break
            self._pools[provider] = pool

    def has_any(self, provider: str) -> bool:
        pool = self._pools.get(provider)
        return bool(pool and pool.credentials)

    def next_for(self, provider: str) -> Credential | None:
        pool = self._pools.get(provider)
        return pool.next_available() if pool else None

    def unavailable_reason(self, provider: str) -> str:
        """Why this provider cannot be used right now, for the selection log."""
        pool = self._pools.get(provider)
        if pool is None or not pool.credentials:
            env_var = _PROVIDER_ENV_VARS.get(provider, ("<unknown>",))[-1]
            return f"no credential configured ({env_var} is unset)"

        disabled = [c for c in pool.credentials if c.disabled_reason]
        if len(disabled) == len(pool.credentials):
            return f"all {len(disabled)} key(s) rejected by the provider"
        return "all key(s) cooling down after quota exhaustion"

    def aliases_for(self, provider: str) -> list[str]:
        pool = self._pools.get(provider)
        return [c.alias for c in pool.credentials] if pool else []


_store: CredentialStore | None = None


def get_store() -> CredentialStore:
    global _store
    if _store is None:
        _store = CredentialStore()
    return _store


def reset_store() -> None:
    """Drop the cached store. For tests that change the environment."""
    global _store
    _store = None
