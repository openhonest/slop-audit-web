"""Pure tests for the rate-limit and size guards. assert f(input) == expected."""

from app.logic.guards import evaluate_rate_limit, size_exceeds


def test_allows_when_under_limit_and_records_now():
    assert evaluate_rate_limit([], now=100.0, max_requests=3, window_seconds=60) == {
        "allowed": True,
        "retained": [100.0],
    }


def test_allows_up_to_the_limit():
    d = evaluate_rate_limit([100.0, 101.0], now=102.0, max_requests=3, window_seconds=60)
    assert d["allowed"] is True
    assert d["retained"] == [100.0, 101.0, 102.0]


def test_blocks_at_the_limit_and_does_not_record():
    d = evaluate_rate_limit([100.0, 101.0, 102.0], now=103.0, max_requests=3, window_seconds=60)
    assert d["allowed"] is False
    assert d["retained"] == [100.0, 101.0, 102.0]


def test_expired_timestamps_are_dropped_and_free_a_slot():
    # Two hits, but one is older than the 60s window from now=200.
    d = evaluate_rate_limit([100.0, 190.0], now=200.0, max_requests=2, window_seconds=60)
    assert d["allowed"] is True
    assert d["retained"] == [190.0, 200.0]


def test_window_boundary_is_exclusive():
    # Exactly window_seconds old is treated as expired (now - t == window).
    d = evaluate_rate_limit([140.0], now=200.0, max_requests=1, window_seconds=60)
    assert d["allowed"] is True
    assert d["retained"] == [200.0]


def test_size_exceeds():
    assert size_exceeds(300_001, 300_000) is True
    assert size_exceeds(300_000, 300_000) is False
    assert size_exceeds(0, 300_000) is False
