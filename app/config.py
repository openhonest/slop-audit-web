"""
Application configuration: the one place that reads os.environ.

Every other module takes `config: AppConfig` as an explicit parameter. Hidden
state lives here and nowhere else. `load_config()` is called once in
`app/main.py` and stashed on `app.state.config`.
"""

from __future__ import annotations

import os
from typing import TypedDict


class AppConfig(TypedDict):
    clone_timeout_seconds: float
    analyze_timeout_seconds: float
    work_dir: str
    max_repo_size_kb: int
    github_token: str | None
    rate_limit_max_requests: int
    rate_limit_window_seconds: float


def load_config() -> AppConfig:
    return {
        "clone_timeout_seconds": float(os.environ.get("CLONE_TIMEOUT_SECONDS", "45")),
        "analyze_timeout_seconds": float(os.environ.get("ANALYZE_TIMEOUT_SECONDS", "60")),
        "work_dir": os.environ.get("WORK_DIR", "/tmp/slop-audit-web"),
        "max_repo_size_kb": int(os.environ.get("MAX_REPO_SIZE_KB", "300000")),
        # Absence is a real state (unauthenticated GitHub API), so encode it as
        # None rather than a fake default. Resolved at the boundary in services.
        "github_token": os.environ.get("GITHUB_TOKEN") or None,
        "rate_limit_max_requests": int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "10")),
        "rate_limit_window_seconds": float(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60")),
    }
