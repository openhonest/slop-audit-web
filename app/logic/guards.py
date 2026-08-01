"""
Pure guard logic: rate-limit decisions and repo-size checks.

No clock, no store, no I/O. The caller reads the clock and holds the per-key
history; these functions just decide. That keeps them testable with
`assert f(input) == expected` and no mocks.
"""

from __future__ import annotations

from typing import TypedDict


class RateDecision(TypedDict):
    allowed: bool
    retained: list[float]


def evaluate_rate_limit(
    timestamps: list[float],
    now: float,
    max_requests: int,
    window_seconds: float,
) -> RateDecision:
    """Sliding-window rate limit. `timestamps` are prior hit times on the same
    clock as `now`. Drop anything older than the window, then allow iff fewer
    than `max_requests` remain. When allowed, `now` joins the retained set."""
    fresh = [t for t in timestamps if now - t < window_seconds]
    if len(fresh) < max_requests:
        return {"allowed": True, "retained": [*fresh, now]}
    return {"allowed": False, "retained": fresh}


def size_exceeds(size_kb: int, max_kb: int) -> bool:
    """True when a repo's reported size is over the cap. Equal is allowed."""
    return size_kb > max_kb
