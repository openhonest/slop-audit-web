"""
Pure construction of one permanent audit-log event. No clock, no I/O: the
caller reads the time and appends the line (app/services.py:log_audit_event),
the same logic/services split the rest of this app already uses.
"""

from __future__ import annotations

from typing import TypedDict


class AuditEvent(TypedDict):
    timestamp: str
    endpoint: str
    client_key: str
    url: str
    slug: str | None
    outcome: str
    cache_hit: bool
    duration_ms: float | None
    error: str | None


def build_audit_event(
    *,
    timestamp: str,
    endpoint: str,
    client_key: str,
    url: str,
    slug: str | None,
    outcome: str,
    cache_hit: bool,
    duration_ms: float | None,
    error: str | None,
) -> AuditEvent:
    return {
        "timestamp": timestamp,
        "endpoint": endpoint,
        "client_key": client_key,
        "url": url,
        "slug": slug,
        "outcome": outcome,
        "cache_hit": cache_hit,
        "duration_ms": duration_ms,
        "error": error,
    }
