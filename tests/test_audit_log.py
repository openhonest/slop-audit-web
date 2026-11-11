"""Pure tests for the audit-log event builder. assert f(input) == expected."""

from app.logic.audit_log import build_audit_event


def test_success_event_shape():
    event = build_audit_event(
        timestamp="2026-11-11T22:00:00+00:00",
        endpoint="audit",
        client_key="1.2.3.4",
        url="https://github.com/openhonest/slop-audit",
        slug="openhonest/slop-audit",
        outcome="success",
        cache_hit=False,
        duration_ms=842.5,
        error=None,
    )
    assert event == {
        "timestamp": "2026-11-11T22:00:00+00:00",
        "endpoint": "audit",
        "client_key": "1.2.3.4",
        "url": "https://github.com/openhonest/slop-audit",
        "slug": "openhonest/slop-audit",
        "outcome": "success",
        "cache_hit": False,
        "duration_ms": 842.5,
        "error": None,
    }


def test_error_event_carries_the_message():
    event = build_audit_event(
        timestamp="2026-11-11T22:00:00+00:00",
        endpoint="audit_stream",
        client_key="5.6.7.8",
        url="not-a-repo",
        slug=None,
        outcome="bad_url",
        cache_hit=False,
        duration_ms=None,
        error=None,
    )
    assert event["slug"] is None
    assert event["duration_ms"] is None
    assert event["outcome"] == "bad_url"
