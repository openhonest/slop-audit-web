"""Pure tests for GitHub URL parsing. assert f(input) == expected, no mocks."""

from app.logic.repo import parse_github_url


def test_bare_owner_repo():
    assert parse_github_url("openhonest/slop-audit") == {
        "owner": "openhonest",
        "name": "slop-audit",
        "slug": "openhonest/slop-audit",
        "clone_url": "https://github.com/openhonest/slop-audit.git",
    }


def test_full_url():
    assert parse_github_url("https://github.com/openhonest/umbra")["slug"] == "openhonest/umbra"


def test_strips_dot_git():
    assert parse_github_url("https://github.com/openhonest/umbra.git")["name"] == "umbra"


def test_ignores_extra_path_segments():
    assert parse_github_url("https://github.com/openhonest/umbra/tree/main")["slug"] == "openhonest/umbra"


def test_host_relative_and_www():
    assert parse_github_url("github.com/a/b")["slug"] == "a/b"
    assert parse_github_url("www.github.com/a/b")["slug"] == "a/b"


def test_rejects_non_github_host():
    assert parse_github_url("https://gitlab.com/a/b") is None


def test_rejects_incomplete():
    assert parse_github_url("openhonest") is None
    assert parse_github_url("") is None


def test_rejects_path_traversal_and_unsafe_chars():
    assert parse_github_url("../../etc/passwd") is None
    assert parse_github_url("owner/repo;rm -rf /") is None
    assert parse_github_url("owner/re po") is None
