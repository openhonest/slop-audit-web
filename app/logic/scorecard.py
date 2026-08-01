"""
Pure mapping from raw Slop Audit indicator results to a scorecard the page can
tell a story with. No I/O. `build_scorecard(slug, lang, results)` is testable
directly: assert it equals the expected view model.

All user-facing wording lives in app/copy.md and is loaded through app.copy. This
module holds only the logic: which band, which indicators, which numbers fill the
{braces}. To reword the page, edit copy.md, not this file.

Two things the logic must never get wrong (load-bearing honesty, not style):
  - L1.18 / L1.19 / L1.20 are finite-testability indicators, NOT mapped to any of
    the 18 compliance dimensions. They get their own group and no dimension tag.
  - L1.15 maps to Dependency injection (4.12), not a "type safety" dimension.
The hero answers "how many end-to-end test cases would fully cover this code?"
For code with unbounded mutable state that is infinite; for pure code it is a
small, attainable number (the edge cover from the analyzer's path_cover).
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from app.copy import text

# The analyzer reports the counts inside L1.18's detail string, e.g.
# "2/63 functions reference external mutable state (python)".
_FUNC_COUNTS = re.compile(r"(\d+)\s*/\s*(\d+)\s+functions reference external mutable state")

_INFINITE_BANDS = frozenset({"Healthy", "Not Healthy", "Slop"})


class DimensionRef(TypedDict):
    dimension: str
    frameworks: str


class Metric(TypedDict):
    label: str
    tech: str
    value: str
    band: str
    band_word: str
    meaning: str
    group: str
    maps_to: list[DimensionRef]


class Scorecard(TypedDict):
    slug: str
    lang: str
    question: str
    qualifier: str
    answer: str          # "∞", "", "Finite", or "n/a"
    kind: str            # "infinite" | "finite" | "n/a"
    verdict_line: str
    paths: int | None    # finite case: minimum runs that walk every reachable branch
    detail: str
    status: str
    band: str
    band_word: str
    mutable_state: str
    finite_funcs: int | None
    infinite_funcs: int | None
    total_funcs: int | None
    decision_points: int | None
    culprits: list[dict[str, Any]]   # the specific functions that make it uncoverable
    culprits_more: int               # how many culprits beyond the shown cap
    core: list[Metric]
    audit: list[Metric]
    share_text: str


_BAND_WORD: dict[str, str] = {
    "Healthy": "Clean",
    "Not Healthy": "Caution",
    "Slop": "Slop",
    "n/a": "No data",
}

# Indicator display order and structural data. Wording (label / tech / meaning)
# lives in copy.md, keyed by the indicator number. `maps_to` is empty for the
# finite-testability core by design.
_CORE: tuple[dict[str, Any], ...] = (
    {"key": "L1.18", "unit": "%", "maps_to": []},
    {"key": "L1.19", "unit": "", "maps_to": []},
)
_AUDIT: tuple[dict[str, Any], ...] = (
    {"key": "L1.15", "unit": "/kloc", "maps_to": [
        {"dimension": "Dependency injection · 4.12", "frameworks": "NIST SA-11 · ISO/IEC 25010 (testability)"}]},
    {"key": "L1.17", "unit": "%", "maps_to": [
        {"dimension": "Tech-debt management · 4.17", "frameworks": "NIST CM-8 / SA-15 · SOC 2 CC7.1 · ISO/IEC 25010"}]},
    {"key": "L1.16", "unit": "%", "maps_to": [
        {"dimension": "SDLC with AI safeguards · 4.16", "frameworks": "NIST SA-3 / SA-8 · SOC 2 CC8.1 · OSFI B-13 §4.1.3"}]},
    {"key": "L1.10", "unit": "", "maps_to": [
        {"dimension": "CI/CD · 4.10", "frameworks": "NIST SA-11 / SA-15 / CM-3 · SOC 2 CC8.1 · OSFI B-13 §4.7 · SSDF PW.7"}]},
    {"key": "L1.11", "unit": "", "maps_to": [
        {"dimension": "Containerization · 4.11", "frameworks": "NIST SP 800-190 · SP 800-53 SA-11 / SI-7"}]},
    {"key": "L1.9", "unit": "", "maps_to": [
        {"dimension": "CI/CD · 4.10 + SDLC safeguards · 4.16", "frameworks": "NIST SA-11 · SOC 2 CC8.1"}]},
)


def _value_str(result: dict[str, Any], unit: str) -> str:
    value = result.get("value", "n/a")
    if value == "n/a":
        return "n/a"
    return f"{value}{unit}"


def _func_counts(l18: dict[str, Any]) -> tuple[int, int] | None:
    match = _FUNC_COUNTS.search(str(l18.get("details", "")))
    if match is None:
        return None
    mutable, total = int(match.group(1)), int(match.group(2))
    if total <= 0:
        return None
    return mutable, total


def _metric(spec: dict[str, Any], result: dict[str, Any], group: str) -> Metric:
    band = str(result.get("band", "n/a"))
    key = spec["key"]
    return {
        "label": text(f"label.{key}"),
        "tech": text(f"tech.{key}"),
        "value": _value_str(result, spec["unit"]),
        "band": band,
        "band_word": _BAND_WORD.get(band, "No data"),
        "meaning": text(f"meaning.{key}"),
        "group": group,
        "maps_to": spec["maps_to"],
    }


def _metrics(specs: tuple[dict[str, Any], ...], results: dict[str, Any], group: str) -> list[Metric]:
    return [_metric(spec, results[spec["key"]], group) for spec in specs if spec["key"] in results]


def _coverage(band: str, counts: tuple[int, int] | None, cover: int | None) -> dict[str, Any]:
    """The hero answer + explanation. Infinite when any function reads mutable
    state; otherwise finite, and `cover` (path_cover) is the attainable number."""
    if counts is None or band == "n/a":
        return {
            "answer": "n/a", "kind": "n/a", "qualifier": "", "verdict_line": "", "paths": None,
            "detail": text("detail.na"), "status": "",
            "finite_funcs": None, "infinite_funcs": None, "total_funcs": None,
        }
    mutable, total = counts
    finite = total - mutable
    common = {"finite_funcs": finite, "infinite_funcs": mutable, "total_funcs": total}
    if mutable > 0:
        plural = "function" if mutable == 1 else "functions"
        return {
            "answer": "∞", "kind": "infinite", "qualifier": "", "paths": None,
            "verdict_line": text("verdict.infinite"),
            "detail": text("detail.infinite", mutable=f"{mutable:,}", total=f"{total:,}", plural=plural),
            "status": text(f"status.infinite.{band}") if band in _INFINITE_BANDS else "",
            **common,
        }
    # Finite: full verification is possible. Green only, no status line, no giant
    # number. The detail names the edge-cover count; if it is somehow absent the
    # verdict stands on its own.
    return {
        "answer": "", "kind": "finite", "qualifier": "", "paths": cover,
        "verdict_line": text("verdict.finite"),
        "detail": text("detail.finite", cover=f"{cover:,}") if cover else "",
        "status": "",
        **common,
    }


def _share_text(slug: str, cov: dict[str, Any]) -> str:
    if cov["kind"] == "infinite":
        return text("share.infinite", slug=slug,
                    mutable=f"{cov['infinite_funcs']:,}", total=f"{cov['total_funcs']:,}")
    if cov["kind"] == "finite":
        return text("share.finite", slug=slug)
    return text("share.na", slug=slug)


_CULPRIT_CAP = 25


def _culprits(l18b: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """The specific functions that make coverage impossible or unknown, from the
    L1.18b state-bounds findings. Unbounded first, then undetermined; bounded
    functions are not problems and are dropped."""
    findings = l18b.get("findings", []) if isinstance(l18b, dict) else []
    order = {"unbounded": 0, "undetermined": 1}
    flagged = sorted(
        (f for f in findings if f.get("verdict") in order),
        key=lambda f: (order[f["verdict"]], f.get("file", ""), f.get("line", 0)),
    )
    shown = [
        {
            "file": f.get("file", ""),
            "line": f.get("line", 0),
            "function": f.get("function", "?"),
            "verdict": f.get("verdict", ""),
            "state": ", ".join(f.get("state", [])) or "(state not located)",
        }
        for f in flagged[:_CULPRIT_CAP]
    ]
    return shown, max(0, len(flagged) - _CULPRIT_CAP)


def build_scorecard(slug: str, lang: str, results: dict[str, Any]) -> Scorecard:
    l18 = results.get("L1.18", {"value": "n/a", "band": "n/a"})
    band = str(l18.get("band", "n/a"))
    l19 = results.get("L1.19", {})
    decisions = l19.get("value") if isinstance(l19.get("value"), int) else None
    pc = results.get("path_cover", {})
    cover = pc.get("value") if isinstance(pc.get("value"), int) else None

    cov = _coverage(band, _func_counts(l18), cover)
    culprits, culprits_more = _culprits(results.get("L1.18b", {}))

    return {
        "slug": slug,
        "lang": lang,
        "question": text("question"),
        "qualifier": cov["qualifier"],
        "answer": cov["answer"],
        "kind": cov["kind"],
        "verdict_line": cov["verdict_line"],
        "paths": cov["paths"],
        "detail": cov["detail"],
        "status": cov["status"],
        "band": band,
        "band_word": _BAND_WORD.get(band, "No data"),
        "mutable_state": _value_str(l18, "%"),
        "finite_funcs": cov["finite_funcs"],
        "infinite_funcs": cov["infinite_funcs"],
        "total_funcs": cov["total_funcs"],
        "decision_points": decisions,
        "culprits": culprits,
        "culprits_more": culprits_more,
        "core": _metrics(_CORE, results, "core"),
        "audit": _metrics(_AUDIT, results, "audit"),
        "share_text": _share_text(slug, cov),
    }
