"""Pure tests for the work-dir sweep decision. assert f(input) == expected."""

from app.logic.sweep import stale_names


def test_empty_mapping_sweeps_nothing():
    assert stale_names({}, max_age_seconds=900, now=1000.0) == []


def test_fresh_entry_is_kept():
    assert stale_names({"owner-repo-abcd1234": 999.5}, max_age_seconds=900, now=1000.0) == []


def test_stale_entry_is_flagged():
    assert stale_names({"owner-repo-abcd1234": 50.0}, max_age_seconds=900, now=1000.0) == ["owner-repo-abcd1234"]


def test_age_boundary_is_exclusive():
    # Exactly max_age_seconds old is not yet stale (strictly greater only).
    assert stale_names({"x": 100.0}, max_age_seconds=900, now=1000.0) == []
    assert stale_names({"x": 99.0}, max_age_seconds=900, now=1000.0) == ["x"]


def test_mixed_entries_only_flags_the_stale_ones():
    mtimes = {"fresh": 999.0, "stale-one": 10.0, "stale-two": 5.0}
    assert sorted(stale_names(mtimes, max_age_seconds=900, now=1000.0)) == ["stale-one", "stale-two"]
