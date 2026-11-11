"""
Pure decision: which work-dir entries are old enough to be orphans.

A clone or analyze step that gets killed mid-flight (process restart, OOM, a
client disconnecting an SSE stream before the route's `finally: rmtree` runs)
leaves its temp directory behind with nothing to clean it up. This decides
which entries are stale enough to be exactly that, from a plain name->mtime
mapping the caller already read, so it needs no filesystem access of its own.
"""

from __future__ import annotations


def stale_names(mtimes: dict[str, float], max_age_seconds: float, now: float) -> list[str]:
    """Names whose mtime is older than max_age_seconds."""
    return [name for name, mtime in mtimes.items() if now - mtime > max_age_seconds]
