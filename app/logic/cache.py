"""
Pure cache decisions for audit results: whether a slug's result is still
fresh, and what to store for it. No clock, no dict ownership: the caller
holds the state (app.state.result_cache) and passes it in, the same split
guards.py already uses for the rate limiter. That keeps this testable with
`assert f(input) == expected` and no mocks.
"""

from __future__ import annotations

from typing import Any, TypedDict


class CacheEntry(TypedDict):
    expires_at: float
    lang: str
    results: dict[str, Any]


def cached_result(cache: dict[str, CacheEntry], slug: str, now: float) -> tuple[str, dict[str, Any]] | None:
    """The cached (lang, results) for slug, or None if absent or expired.
    Never mutates cache; an expired entry is just not returned, left for a
    later write to replace."""
    entry = cache.get(slug)
    if entry is None or now >= entry["expires_at"]:
        return None
    return entry["lang"], entry["results"]


def cache_entry(lang: str, results: dict[str, Any], now: float, ttl_seconds: float) -> CacheEntry:
    """The entry to store for a slug, valid until now + ttl_seconds."""
    return {"expires_at": now + ttl_seconds, "lang": lang, "results": results}
