"""
Pure mapping from raw Slop Audit indicator results to a scorecard the page can
tell a story with. No I/O. `build_scorecard(slug, lang, results)` is testable
directly: assert it equals the expected view model.

All user-facing wording lives in app/copy.md and is loaded through app.copy. This
module holds only the logic: which status, which indicators, which numbers fill the
{braces}. To reword the page, edit copy.md, not this file.

The hero answers "can this code be exhaustively tested?" from the finite-testability
meter (L1.18b), which returns three verdicts per piece of state:

  - any PROMISCUOUS state -> "cannot" (red): a reaching partition is provably
    unbounded, so no finite test suite covers it. Mathematically impossible.
  - else any UNRESOLVED   -> "might" (yellow): nothing is provably unbounded, but
    the analyzer could not statically decide some state (dynamic dispatch,
    reflection). Resolvable; the culprits list is what to fix.
  - else all NEUTRAL      -> "can" (green): every piece of state is reached by a
    finite set of decisions. Finitely testable, and path_cover is the run count.
  - L1.18 n/a             -> "na": no source in a language the analyzer reads.

The value-count L1.18 scalar is retained and shown as a secondary number (the v1
mutable-state ratio), NOT as the hero verdict.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.copy import text

_ZERO_COUNTS = {"neutral": 0, "promiscuous": 0, "unresolved": 0}
_CULPRIT_CAP = 25
# Which verdict is the culprit for each status: the promiscuous state proves
# "cannot"; the unresolved state is what you resolve to escape "might".
_WANT = {"cannot": "promiscuous", "might": "unresolved"}


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
    status: str          # "can" | "might" | "cannot" | "na"
    grade: str | None    # single headline letter: A/B/C (CAN), D (MIGHT), F (CANNOT); None for na
    grade_pct: int | None   # the finitely-testable share behind the grade, e.g. 72
    headline: str        # the green/yellow/red sentence
    detail: str
    paths: int | None    # "can" only: fewest runs that walk every reachable branch
    band: str
    band_word: str
    mutable_state: str   # L1.18 mutable-state ratio, shown as a secondary metric
    resolvable: str      # L1.18b resolvable fraction, e.g. "95%"
    testable: str | None   # share of state that is finitely testable, e.g. "72%"; 100% = fully testable
    neutral_count: int
    promiscuous_count: int
    unresolved_count: int
    decision_points: int | None
    culprits_heading: str
    culprits_note: str
    culprits: list[dict[str, Any]]   # the state that decides the verdict (per piece of state)
    culprits_more: int
    scoped_out: dict[str, Any] | None   # files the meter excluded (docs/tooling/scripts), disclosed
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


def _pct(frac: Any) -> str:
    return f"{round(frac * 100)}%" if isinstance(frac, (int, float)) else "n/a"


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


def _meter_ran(l18b: dict[str, Any]) -> bool:
    """True iff the finite-testability meter produced a real result for this language.
    classify()'s _na (a language the meter has no spec for) sets resolvable_fraction
    to the string "n/a"; a real run sets a float. This sentinel separates "analyzed,
    found nothing unbounded" (a legitimate green) from "never analyzed" (must be na)."""
    return isinstance(l18b, dict) and isinstance(l18b.get("resolvable_fraction"), (int, float))


def _hero_status(band: str, counts: dict[str, int], meter_ran: bool) -> str:
    # NA unless the finite-testability meter itself ran. Keying this off L1.18
    # (mutable-state, which covers more languages than the verdict meter) rendered a
    # false green: a language the meter has no spec for scored 0 pieces of state and
    # the card claimed "definitely CAN / 100% testable". The meter's own result is the
    # only honest source of the verdict.
    if not meter_ran or band == "n/a":
        return "na"
    if counts.get("promiscuous", 0) > 0:
        return "cannot"
    if counts.get("unresolved", 0) > 0:
        return "might"
    return "can"


def _culprits(l18b: dict[str, Any], status: str) -> tuple[list[dict[str, Any]], int]:
    """The state that decides the verdict, per piece of state (class/module scope).
    For 'cannot' the provably-unbounded (promiscuous) state; for 'might' the
    undecidable (unresolved) state. Decision-driving state first."""
    want = _WANT.get(status)
    if want is None:
        return [], 0
    findings = l18b.get("findings", []) if isinstance(l18b, dict) else []
    flagged = [f for f in findings if f.get("verdict") == want]
    flagged.sort(key=lambda f: (not f.get("drives_decision", False), f.get("file", ""), f.get("line", 0)))
    shown = [
        {
            "file": f.get("file", ""),
            "line": f.get("line", 0),
            "state": f.get("state", "?"),
            "verdict": f.get("verdict", ""),
            "drives_decision": bool(f.get("drives_decision", False)),
        }
        for f in flagged[:_CULPRIT_CAP]
    ]
    return shown, max(0, len(flagged) - _CULPRIT_CAP)


def _scoped_out(l18b: dict[str, Any]) -> dict[str, Any] | None:
    """What the meter chose not to look at, surfaced so the reader can challenge it
    (the cone of light on scope). None when nothing was bucketed."""
    bucketed = l18b.get("bucketed", {}) if isinstance(l18b, dict) else {}
    counts = bucketed.get("counts", {}) or {}
    paths = [p["path"] for p in bucketed.get("paths", [])]   # docs / tooling / loose scripts
    total = sum(counts.values())
    if not total:
        return None
    return {
        "total": total,
        "reasons": ", ".join(f"{n} {r}" for r, n in sorted(counts.items())),
        "paths": paths[:12],
        "paths_more": max(0, len(paths) - 12),
    }


# Weighted importance of the audit indicators for the passing tier (CAN -> A/B/C).
# PUBLISHED, not hidden (the whole point vs opaque security ratings): god-files and
# type-escapes are the strongest AI-slop / discipline smells, then verification gates,
# then reproducibility and formatting. Tune these in the open, in this table.
_HYGIENE_WEIGHTS = {"L1.17": 3, "L1.15": 3, "L1.10": 2, "L1.11": 1, "L1.9": 1, "L1.16": 1}
_BAND_POINTS = {"Healthy": 1.0, "Not Healthy": 0.5, "Slop": 0.0}
_A_MIN, _B_MIN = 0.85, 0.60


def _hygiene_score(results: dict[str, Any]) -> float | None:
    """Weighted health of the audit indicators, 0..1. An indicator with no band (n/a
    or not computed) is excluded, not counted against the repo. None if none ran."""
    num = den = 0.0
    for key, weight in _HYGIENE_WEIGHTS.items():
        points = _BAND_POINTS.get(str(results.get(key, {}).get("band")))
        if points is None:
            continue
        num += weight * points
        den += weight
    return (num / den) if den else None


def _grade(status: str, pct: int | None, hygiene: float | None) -> str | None:
    """The single headline grade, verifiability-first, by a published rule. The
    finite-testability verdict sets the tier: CANNOT (provably unbounded state) is a
    categorical F; MIGHT (undetermined, not proven bad) a D. Within the passing tier
    (CAN - every piece of state finitely testable), A/B/C is the weighted health of the
    audit indicators, so a fully-testable repo with poor hygiene lands below A."""
    if status == "na" or pct is None:
        return None
    if status == "cannot":
        return "F"
    if status == "might":
        return "D"
    if hygiene is None:
        return "A"
    return "A" if hygiene >= _A_MIN else "B" if hygiene >= _B_MIN else "C"


def _detail(status: str, promiscuous: int, cover: int | None) -> str:
    if status == "na":
        return text("detail.na")
    if status == "cannot":
        return text("detail.cannot", n=promiscuous, plural="piece" if promiscuous == 1 else "pieces")
    if status == "can":
        return text("detail.can", cover=f"{cover:,}") if cover else text("detail.can_nocover")
    return text("detail.might")


def build_scorecard(slug: str, lang: str, results: dict[str, Any]) -> Scorecard:
    l18 = results.get("L1.18", {"value": "n/a", "band": "n/a"})
    band = str(l18.get("band", "n/a"))
    l18b = results.get("L1.18b", {})
    l18b = l18b if isinstance(l18b, dict) else {}
    counts = l18b.get("counts") or _ZERO_COUNTS
    status = _hero_status(band, counts, _meter_ran(l18b))
    total_state = sum(counts.values())
    # Share of state that is finitely testable: 100% = fully testable, 0% = none.
    # No state at all is trivially fully testable. Undetermined counts against it.
    pct = None if status == "na" else (100 if total_state == 0 else round(counts.get("neutral", 0) / total_state * 100))
    testable = None if pct is None else f"{pct}%"
    grade = _grade(status, pct, _hygiene_score(results))

    pc = results.get("path_cover", {})
    cover = pc.get("value") if isinstance(pc.get("value"), int) else None
    l19 = results.get("L1.19", {})
    decisions = l19.get("value") if isinstance(l19.get("value"), int) else None

    culprits, culprits_more = _culprits(l18b, status)
    promiscuous = counts.get("promiscuous", 0)

    return {
        "slug": slug,
        "lang": lang,
        "question": text("question"),
        "status": status,
        "grade": grade,
        "grade_pct": pct,
        "headline": "" if status == "na" else text(f"headline.{status}"),
        "detail": _detail(status, promiscuous, cover),
        "paths": cover if status == "can" else None,
        "band": band,
        "band_word": _BAND_WORD.get(band, "No data"),
        "mutable_state": _value_str(l18, "%"),
        "resolvable": _pct(l18b.get("resolvable_fraction")),
        "testable": testable,
        "neutral_count": counts.get("neutral", 0),
        "promiscuous_count": promiscuous,
        "unresolved_count": counts.get("unresolved", 0),
        "decision_points": decisions,
        "culprits_heading": text(f"culprits.heading.{status}") if status in _WANT else "",
        "culprits_note": text(f"culprits.note.{status}") if status in _WANT else "",
        "culprits": culprits,
        "culprits_more": culprits_more,
        "scoped_out": _scoped_out(l18b),
        "core": _metrics(_CORE, results, "core"),
        "audit": _metrics(_AUDIT, results, "audit"),
        "share_text": text(f"share.{status}", slug=slug),
    }
