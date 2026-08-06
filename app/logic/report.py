"""Render a scorecard as Markdown, for the MCP server and any agent-facing output.

Pure: `scorecard_markdown(card)` takes the view model build_scorecard produces and
returns Markdown. No I/O. The same numbers the web card shows, in the form a coding
agent can read inline: the grade, the verdict, the state that limits it (file:line),
and the audit checks, plus the rule the grade was computed by.
"""

from __future__ import annotations

from app.logic.scorecard import Scorecard

_VERDICT_LINE = {
    "can": "CAN be exhaustively tested.",
    "might": "MIGHT be exhaustively testable (some state is undetermined).",
    "cannot": "CANNOT be exhaustively tested (some state is provably unbounded).",
    "na": "not analyzable (no source in a language the analyzer reads).",
}


def scorecard_markdown(card: Scorecard) -> str:
    slug, lang = card["slug"], card["lang"]
    lines: list[str] = [f"# Slop Audit — {slug} ({lang})", ""]

    if card["status"] == "na":
        lines += [f"This repo is {_VERDICT_LINE['na']}", "", card["detail"]]
        return "\n".join(lines)

    grade = card.get("grade")
    pct = card.get("grade_pct")
    if grade is not None:
        lines.append(f"**Grade: {grade}** — {pct}% of its state is finitely testable")
        lines.append("")
    lines.append(f"This code {_VERDICT_LINE.get(card['status'], '')}")
    lines.append("")
    lines.append(
        f"- Finitely testable: {card['neutral_count']}\n"
        f"- Provably unbounded: {card['promiscuous_count']}\n"
        f"- Undetermined: {card['unresolved_count']}"
    )
    if card["status"] == "can" and card.get("paths"):
        lines.append(f"- Runs that cover every branch: {card['paths']:,}")

    culprits = card.get("culprits") or []
    if culprits:
        lines += ["", f"## {card.get('culprits_heading') or 'What limits it'}", ""]
        for c in culprits:
            drives = ", drives a decision" if c.get("drives_decision") else ""
            lines.append(f"- `{c['file']}:{c['line']}` — `{c['state']}` ({c['verdict']}{drives})")
        if card.get("culprits_more"):
            lines.append(f"- …and {card['culprits_more']} more")

    audit = card.get("audit") or []
    if audit:
        lines += ["", "## Audit checks", "", "| Check | Value | Band |", "|---|---|---|"]
        for m in audit:
            lines.append(f"| {m['tech']} | {m['value']} | {m['band']} |")

    ts = card.get("thread_surface")
    if ts:
        lines += ["", f"## Thread-safety surface — {ts['verdict']}", "", ts["blurb"]]
        if ts.get("sites"):
            lines += ["", "| Site | Kind | Symbol |", "|---|---|---|"]
            for s in ts["sites"]:
                lines.append(f"| `{s['file']}:{s['line']}` | {s['kind']} | `{s['symbol']}` |")
            if ts.get("sites_more"):
                lines.append(f"- …and {ts['sites_more']} more")
        lines += [
            "",
            "> Audit surface, not a race verdict. This does not detect data races "
            "(that needs ThreadSanitizer at runtime); a site here means \"verify this\", "
            "never \"a race exists\".",
        ]

    lines += [
        "",
        "## How the grade is computed",
        "",
        "Verifiability first, by a published rule. The verdict sets the tier: CANNOT is F, "
        "MIGHT is D. When every piece of state is finitely testable, A/B/C is the weighted "
        "health of the audit checks above (god-files and type-escapes weigh most). "
        "Full methodology: https://slopaudit.org",
    ]
    return "\n".join(lines)
