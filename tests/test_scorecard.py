"""Pure tests for the scorecard view model. assert f(input) == expected, no mocks.

The hero is driven by the finite-testability meter (L1.18b), not the value-count
L1.18 scalar: any promiscuous state -> cannot; else any unresolved -> might; else
all neutral -> can. The L1.18 scalar is retained only as a secondary number.
"""

from app.logic.scorecard import build_scorecard


def _l18b(neutral=0, promiscuous=0, unresolved=0, findings=None, resolvable=1.0):
    return {
        "counts": {"neutral": neutral, "promiscuous": promiscuous, "unresolved": unresolved},
        "resolvable_fraction": resolvable,
        "findings": findings or [],
    }


# Value-count says 12% mutable (old model would call this "infinite"), but every
# piece of state is neutral under partition-count -> definitely testable.
CAN = {
    "lang": "python",
    "L1.18": {"value": 12.0, "band": "Healthy", "details": "5/40 functions reference external mutable state (python)"},
    "L1.18b": _l18b(neutral=8, resolvable=1.0),
    "L1.19": {"value": 10, "band": "n/a"},
    "path_cover": {"value": 7, "band": "n/a"},
}

MIGHT = {
    "lang": "python",
    "L1.18": {"value": 30.0, "band": "Slop", "details": "9/30 functions reference external mutable state (python)"},
    "L1.18b": _l18b(neutral=5, unresolved=3, resolvable=0.625, findings=[
        {"file": "r.py", "line": 12, "state": "self.handler", "verdict": "unresolved", "drives_decision": True},
        {"file": "p.py", "line": 4, "state": "self.value", "verdict": "unresolved", "drives_decision": True},
        {"file": "z.py", "line": 9, "state": "self.mode", "verdict": "neutral", "drives_decision": True},
    ]),
}

CANNOT = {
    "lang": "python",
    "L1.18": {"value": 47.0, "band": "Slop", "details": "20/63 functions reference external mutable state (python)"},
    "L1.18b": _l18b(neutral=4, promiscuous=2, unresolved=1, resolvable=0.857, findings=[
        {"file": "a.py", "line": 10, "state": "self.cache", "verdict": "promiscuous", "drives_decision": True},
        {"file": "g.py", "line": 2, "state": "_registry", "verdict": "promiscuous", "drives_decision": True},
        {"file": "c.py", "line": 3, "state": "self.sink", "verdict": "unresolved", "drives_decision": True},
        {"file": "b.py", "line": 5, "state": "self.flag", "verdict": "neutral", "drives_decision": True},
    ]),
    "L1.15": {"value": 6.68, "band": "Slop"},
    "L1.17": {"value": 0.0, "band": "Healthy"},
    "L1.16": {"value": 0.0, "band": "Healthy"},
    "L1.10": {"value": 1, "band": "Not Healthy"},
    "L1.11": {"value": "absent", "band": "Slop"},
    "L1.9": {"value": "present", "band": "Healthy"},
}

NA = {"lang": "unknown", "L1.18": {"value": "n/a", "band": "n/a"}}


def test_can_when_all_state_is_neutral():
    card = build_scorecard("owner/repo", "python", CAN)
    assert card["status"] == "can"
    assert card["headline"]
    assert card["paths"] == 7                 # only the green case shows the run count
    assert card["culprits"] == []
    assert card["resolvable"] == "100%"


def test_might_when_unresolved_but_no_promiscuous():
    card = build_scorecard("owner/repo", "python", MIGHT)
    assert card["status"] == "might"
    assert card["paths"] is None
    # culprits are the unresolved state (decision-driving first, then by file), not the neutral one
    assert [c["state"] for c in card["culprits"]] == ["self.value", "self.handler"]
    assert all(c["verdict"] == "unresolved" for c in card["culprits"])
    assert card["culprits_heading"]


def test_cannot_when_any_promiscuous():
    card = build_scorecard("owner/repo", "python", CANNOT)
    assert card["status"] == "cannot"
    assert card["paths"] is None
    # culprits are the promiscuous state only (the proof), not the unresolved/neutral
    assert [c["state"] for c in card["culprits"]] == ["self.cache", "_registry"]
    assert all(c["verdict"] == "promiscuous" for c in card["culprits"])
    assert card["promiscuous_count"] == 2
    assert "{n}" not in card["detail"] and "2" in card["detail"]   # {n} filled from the count


def test_na_when_no_recognized_source():
    card = build_scorecard("owner/repo", "unknown", NA)
    assert card["status"] == "na"
    assert card["headline"] == ""
    assert card["culprits"] == []


def test_mutable_state_scalar_retained_as_secondary_number():
    card = build_scorecard("owner/repo", "python", CANNOT)
    assert card["mutable_state"] == "47.0%"   # the v1 value-count scalar is still shown


def test_core_group_has_no_dimension_tags_audit_group_does():
    card = build_scorecard("owner/repo", "python", CANNOT)
    assert all(m["maps_to"] == [] for m in card["core"])
    assert all(m["maps_to"] for m in card["audit"])
    by_tech = {m["tech"]: m for m in card["audit"]}
    assert by_tech["L1.15 · type-escape density"]["maps_to"][0]["dimension"] == "Dependency injection · 4.12"


def test_share_text_includes_the_slug():
    for results in (CAN, MIGHT, CANNOT):
        card = build_scorecard("owner/repo", "python", results)
        assert "owner/repo" in card["share_text"]


def test_scoped_out_is_disclosed_when_files_were_bucketed():
    results = dict(CANNOT)
    results["L1.18b"] = dict(results["L1.18b"], bucketed={
        "counts": {"docs": 2, "tests": 15, "root-script": 1},
        "paths": [{"path": "docs/conf.py", "reason": "docs"}, {"path": "mutate.py", "reason": "root-script"}],
    })
    card = build_scorecard("owner/repo", "python", results)
    assert card["scoped_out"]["total"] == 18
    assert "docs/conf.py" in card["scoped_out"]["paths"]
    assert "docs" in card["scoped_out"]["reasons"]


def test_no_scoped_out_when_nothing_was_bucketed():
    assert build_scorecard("owner/repo", "python", CAN)["scoped_out"] is None


def test_testable_percentage_is_the_share_of_finitely_testable_state():
    # 100% when all state is neutral, a lower fraction otherwise, None when n/a.
    assert build_scorecard("owner/repo", "python", CAN)["testable"] == "100%"       # 8 of 8
    assert build_scorecard("owner/repo", "python", CANNOT)["testable"] == "57%"      # 4 of 7
    assert build_scorecard("owner/repo", "python", NA)["testable"] is None
