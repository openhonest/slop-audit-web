"""Pure tests for the scorecard view model. assert f(input) == expected, no mocks."""

from app.logic.scorecard import build_scorecard

# openhonest/slop-audit shape: 2 of 63 functions read mutable state -> infinite.
INFINITE = {
    "lang": "python",
    "L1.18": {"value": 3.2, "band": "Healthy", "details": "2/63 functions reference external mutable state (python)"},
    "L1.19": {"value": 312, "band": "n/a"},
    "L1.15": {"value": 6.68, "band": "Slop"},
    "L1.17": {"value": 0.0, "band": "Healthy"},
    "L1.16": {"value": 0.0, "band": "Healthy"},
    "L1.10": {"value": 1, "band": "Not Healthy"},
    "L1.11": {"value": "absent", "band": "Slop"},
    "L1.9": {"value": "present", "band": "Healthy"},
}

# A hypothetical pure repo: 0 of 40 functions read mutable state -> finite.
PURE = {
    "lang": "python",
    "L1.18": {"value": 0.0, "band": "Healthy", "details": "0/40 functions reference external mutable state (python)"},
    "L1.19": {"value": 10, "band": "n/a"},
    "path_cover": {"value": 7, "band": "n/a"},
}


def test_infinite_answer_when_any_function_reads_mutable_state():
    card = build_scorecard("owner/repo", "python", INFINITE)
    assert card["kind"] == "infinite"
    assert card["answer"] == "∞"
    assert card["infinite_funcs"] == 2
    assert card["finite_funcs"] == 61
    assert card["total_funcs"] == 63
    assert "2 of 63" in card["detail"]


def test_finite_shows_only_green_no_giant_number():
    # Full verification possible: the card shows the edge-cover count and the
    # green verdict, and never the astronomical combination figure.
    card = build_scorecard("owner/repo", "python", PURE)
    assert card["kind"] == "finite"
    assert card["answer"] == ""          # the giant number is not shown at all
    assert card["infinite_funcs"] == 0


def test_finite_leads_with_verdict_and_the_edge_cover_count():
    # Assert structure, not wording: the wording lives in copy.md and is edited freely.
    card = build_scorecard("owner/repo", "python", PURE)
    assert card["verdict_line"]              # a green verdict is shown
    assert card["paths"] == 7                # the edge-cover count from path_cover
    assert "7" in card["detail"]             # the number is filled into the copy
    assert card["status"] == ""              # no separate finite status line


def test_infinite_leads_with_the_bad_news_and_no_practical_count():
    card = build_scorecard("owner/repo", "python", INFINITE)
    assert card["verdict_line"] == "Can't be fully verified."
    assert card["paths"] is None


def test_core_group_has_no_dimension_tags_audit_group_does():
    card = build_scorecard("owner/repo", "python", INFINITE)
    assert all(m["maps_to"] == [] for m in card["core"])
    assert all(m["maps_to"] for m in card["audit"])
    by_tech = {m["tech"]: m for m in card["audit"]}
    assert by_tech["L1.15 · type-escape density"]["maps_to"][0]["dimension"] == "Dependency injection · 4.12"


def test_na_when_no_recognized_source():
    card = build_scorecard("owner/repo", "unknown", {"L1.18": {"value": "n/a", "band": "n/a"}})
    assert card["kind"] == "n/a"
    assert card["answer"] == "n/a"
    assert card["total_funcs"] is None


def test_share_text_includes_the_slug():
    # Wording is in copy.md; only the slug fill-in is guaranteed by the logic.
    card = build_scorecard("owner/repo", "python", INFINITE)
    assert "owner/repo" in card["share_text"]


def test_culprits_enumerate_the_flagged_functions():
    results = {
        "L1.18": {"value": 47.0, "band": "Slop", "details": "2/63 functions reference external mutable state (python)"},
        "L1.18b": {"findings": [
            {"file": "b.py", "line": 5, "function": "bar", "verdict": "bounded", "state": ["self.flag"]},
            {"file": "a.py", "line": 10, "function": "foo", "verdict": "unbounded", "state": ["self.cache"]},
            {"file": "c.py", "line": 3, "function": "baz", "verdict": "undetermined", "state": []},
        ]},
    }
    card = build_scorecard("owner/repo", "python", results)
    # unbounded first, then undetermined; the bounded one is not a problem and is dropped.
    assert [c["function"] for c in card["culprits"]] == ["foo", "baz"]
    assert card["culprits"][0]["file"] == "a.py" and card["culprits"][0]["line"] == 10
    assert card["culprits"][0]["state"] == "self.cache"
    assert card["culprits"][1]["state"] == "(state not located)"
    assert card["culprits_more"] == 0


def test_finite_has_no_culprits():
    card = build_scorecard("owner/repo", "python", PURE)
    assert card["culprits"] == []
