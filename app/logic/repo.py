"""
Pure logic for turning user input into a safe GitHub repository reference.

No I/O. `parse_github_url` returns an explicit Maybe (RepoRef or None); the
route resolves the None case at the boundary. A returned RepoRef is guaranteed
to have owner/name made of a safe character set, so it can be interpolated into
a clone URL without shell or path-traversal risk.
"""

from __future__ import annotations

import re
from typing import TypedDict


class RepoRef(TypedDict):
    owner: str
    name: str
    slug: str
    clone_url: str


_GITHUB_HOSTS = frozenset({"github.com", "www.github.com"})
# A GitHub owner or repo name: letters, digits, hyphen, underscore, dot.
_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def _segments(raw: str) -> list[str]:
    """Strip scheme, host, query/fragment, and a trailing .git, then split the
    path into segments. Pure string work, no network."""
    text = raw.strip()
    text = re.sub(r"^[a-zA-Z]+://", "", text)  # drop scheme
    text = text.split("?", 1)[0].split("#", 1)[0]
    if "/" in text:
        head = text.split("/", 1)[0]
        if "." in head and head.lower() not in _GITHUB_HOSTS:
            return []  # a host we don't accept
        if head.lower() in _GITHUB_HOSTS:
            text = text.split("/", 1)[1]
    parts = [p for p in text.split("/") if p]
    if parts and parts[-1].endswith(".git"):
        parts[-1] = parts[-1][:-4]
    return parts


def _is_safe_segment(segment: str) -> bool:
    return bool(_SEGMENT.match(segment)) and segment not in (".", "..")


def parse_github_url(raw: str) -> RepoRef | None:
    """Parse a GitHub repo reference into a RepoRef, or None if it is not a
    valid public GitHub owner/repo. Accepts full URLs, host-relative paths, and
    bare `owner/repo`."""
    parts = _segments(raw)
    if len(parts) < 2:
        return None
    owner, name = parts[0], parts[1]
    if not (_is_safe_segment(owner) and _is_safe_segment(name)):
        return None
    slug = f"{owner}/{name}"
    return {
        "owner": owner,
        "name": name,
        "slug": slug,
        "clone_url": f"https://github.com/{slug}.git",
    }
