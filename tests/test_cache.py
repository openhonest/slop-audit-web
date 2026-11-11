"""Pure tests for the result cache. assert f(input) == expected."""

from app.logic.cache import cache_entry, cached_result


def test_miss_on_empty_cache():
    assert cached_result({}, "openhonest/slop-audit", now=100.0) is None


def test_hit_before_expiry():
    cache = {"openhonest/slop-audit": cache_entry("python", {"L1.18": 1}, now=100.0, ttl_seconds=3600)}
    assert cached_result(cache, "openhonest/slop-audit", now=200.0) == ("python", {"L1.18": 1})


def test_miss_after_expiry():
    cache = {"openhonest/slop-audit": cache_entry("python", {"L1.18": 1}, now=100.0, ttl_seconds=60)}
    assert cached_result(cache, "openhonest/slop-audit", now=161.0) is None


def test_expiry_boundary_is_exclusive():
    # now - expires_at == 0 counts as expired (now >= expires_at).
    cache = {"slug": cache_entry("python", {}, now=100.0, ttl_seconds=60)}
    assert cached_result(cache, "slug", now=160.0) is None


def test_miss_for_a_different_slug():
    cache = {"owner/one": cache_entry("python", {"a": 1}, now=100.0, ttl_seconds=3600)}
    assert cached_result(cache, "owner/two", now=100.0) is None


def test_cache_entry_shape():
    assert cache_entry("go", {"x": 1}, now=10.0, ttl_seconds=5.0) == {
        "expires_at": 15.0,
        "lang": "go",
        "results": {"x": 1},
    }
