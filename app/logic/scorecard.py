"""
The scorecard the audit page tells its story with. The card model, its prose, the
compliance-framework mappings, and the grade rule all live in ONE place: the engine,
at l1_analyzer.card (shared with the CLI, so the site and the CLI render the SAME card).

This module is the thin web adapter over that shared card. It calls the engine's
build_card with ran_tests=False - the site never executes the repo's code, and the
card's footer says so - then adds the three secondary numbers the page shows that the
CLI card omits (the v1 mutable-state ratio, the resolvable fraction, and the raw
decision-point count). Nothing about the verdict, the grade, the culprits, the audit
mappings, or the thread surface is recomputed here: it comes from the engine.

build_scorecard(slug, lang, results) stays testable directly: assert it equals the
expected view model.
"""

from __future__ import annotations

from typing import Any, TypedDict

from l1_analyzer.card import build_card


class Scorecard(TypedDict, total=False):
    # The engine card's fields, plus the three web-only secondary numbers below. Declared
    # total=False so the web adapter can add its extras without redeclaring the shared shape.
    slug: str
    lang: str
    status: str
    grade: str | None
    grade_pct: int | None
    headline: str
    detail: str
    paths: int | None
    testable: str | None
    culprits: list[dict[str, Any]]
    core: list[dict[str, Any]]
    audit: list[dict[str, Any]]
    thread_surface: dict[str, Any] | None
    scoped_out: dict[str, Any] | None
    share_text: str
    # Web-only secondary numbers (not shown on the CLI card):
    mutable_state: str   # L1.18 value-count ratio, e.g. "47.0%"
    resolvable: str      # L1.18b resolvable fraction, e.g. "95%"
    decision_points: int | None   # L1.19 raw decision count


def _value_str(result: dict[str, Any], unit: str) -> str:
    value = result.get("value", "n/a")
    return "n/a" if value == "n/a" else f"{value}{unit}"


def _pct(frac: object) -> str:
    return f"{round(frac * 100)}%" if isinstance(frac, (int, float)) else "n/a"


def build_scorecard(slug: str, lang: str, results: dict[str, Any]) -> Scorecard:
    # The full card from the shared engine. ran_tests=False: the website is static and
    # never runs the repo's code (the footer says so); the CLI passes ran_tests=True.
    card: dict[str, Any] = dict(build_card(slug, lang, results, ran_tests=False))

    l18 = results.get("L1.18", {"value": "n/a", "band": "n/a"})
    l18b = results.get("L1.18b", {})
    l18b = l18b if isinstance(l18b, dict) else {}
    l19 = results.get("L1.19", {})

    card["mutable_state"] = _value_str(l18, "%")
    card["resolvable"] = _pct(l18b.get("resolvable_fraction"))
    card["decision_points"] = l19.get("value") if isinstance(l19.get("value"), int) else None
    return card  # type: ignore[return-value]
