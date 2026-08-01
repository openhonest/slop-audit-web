"""
I/O boundary: clone a public repo and run the static Slop Audit indicators.

Both functions do real I/O (subprocess, filesystem). Neither ever executes the
target repository's code: the analyzer is called with exec_tests=False, so only
the static source and config indicators run (no test suite is executed). That is
what makes pointing this at an arbitrary public repo safe. Failures surface as
AuditError for the route to turn into a message.
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from l1_analyzer import indicators

from app.config import AppConfig
from app.logic.guards import size_exceeds


class AuditError(Exception):
    """A user-facing failure: bad repo, clone failed, or timeout."""


def check_repo_size(slug: str, config: AppConfig) -> None:
    """Fast pre-clone gate via the GitHub API. Raises AuditError if the repo is
    missing/private or over the size cap. If the API can't be reached (network
    down, unauthenticated rate limit), it returns quietly: the clone timeout is
    the real backstop, so an unverifiable size never blocks a legitimate audit."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "slop-audit-web"}
    token = config["github_token"]
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/repos/{slug}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise AuditError("Couldn't find that repository. Is it public and spelled correctly?") from error
        return  # 403 rate-limit or other API hiccup: fall through to the clone-timeout backstop.
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return
    size_kb = payload.get("size")
    if isinstance(size_kb, int) and size_exceeds(size_kb, config["max_repo_size_kb"]):
        limit_mb = config["max_repo_size_kb"] // 1024
        raise AuditError(f"That repository is too large to audit here (limit {limit_mb} MB). Try the CLI.")


def clone_repo(clone_url: str, dest: Path, config: AppConfig) -> None:
    """Shallow-clone a public repo into dest. Raises AuditError on failure.
    git clone does not run the repository's hooks on the cloning side, so this
    does not execute repo code."""
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", clone_url, str(dest)],
            capture_output=True,
            text=True,
            timeout=config["clone_timeout_seconds"],
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise AuditError("That repository took too long to clone.") from error
    except OSError as error:
        raise AuditError("git is not available to clone the repository.") from error
    if result.returncode != 0:
        raise AuditError("Couldn't clone that repository. Is it public and spelled correctly?")


def analyze_source(path: Path, config: AppConfig) -> dict[str, Any]:
    """Parse the source into syntax trees and compute the source indicators
    (mutable state, decision space, type escapes, ...). Never runs the repo's
    tests: exec_tests=False, so only static structure is measured."""
    return dict(
        indicators.compute_source_indicators(
            path, "auto", exec_tests=False, timeout_seconds=config["analyze_timeout_seconds"]
        )
    )


def analyze_config(path: Path) -> dict[str, Any]:
    """Inspect repo hygiene: CI, containerization, pre-commit. Pure file reads."""
    return dict(indicators.compute_config_indicators(path))


def analyze_repo(path: Path, config: AppConfig) -> tuple[str, dict[str, Any]]:
    """Run all static Slop Audit indicators on a cloned repo. Returns
    (language, merged results). Never executes the repo's tests."""
    source = analyze_source(path, config)
    results: dict[str, Any] = {**analyze_config(path), **source}
    lang = str(results.get("lang", "unknown"))
    return lang, results
