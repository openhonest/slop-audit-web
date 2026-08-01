"""
Single editable source for all user-facing card copy: copy.md.

Edit copy.md to change the wording. Each `## key` section becomes one string,
with newlines collapsed to spaces. `{braces}` are fill-ins the code supplies; a
section with no braces is returned verbatim. A requested key that is missing
fails loud rather than rendering a blank, per "a silent failure is a lie".
"""

from __future__ import annotations

import re
from pathlib import Path

_COPY_PATH = Path(__file__).parent / "copy.md"
# Markdown links in copy.md render as real links: [text](url) -> <a>.
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _render_inline(paragraph: str) -> str:
    collapsed = re.sub(r"\s+", " ", paragraph).strip()
    return _LINK.sub(r'<a href="\2" target="_blank" rel="noopener">\1</a>', collapsed)


def load_copy(path: Path = _COPY_PATH) -> dict[str, str]:
    """Parse copy.md into {key: paragraph}. `## key` starts a section; a top-level
    `# ` heading (a divider) ends the current section without starting one."""
    sections: dict[str, list[str]] = {}
    key: str | None = None
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            key = line[3:].strip()
            sections[key] = []
        elif line.startswith("# "):
            key = None
        elif key is not None:
            sections[key].append(line)
    return {k: _render_inline(" ".join(lines)) for k, lines in sections.items()}


COPY = load_copy()


def text(key: str, **fields: str) -> str:
    if key not in COPY:
        raise KeyError(f"copy.md is missing section: {key!r}")
    value = COPY[key]
    return value.format(**fields) if fields else value
