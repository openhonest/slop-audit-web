# Slop Audit web

Paste a public GitHub repo, get its finite-testability scorecard. A hosted front door for the [Slop Audit](https://github.com/openhonest/slop-audit) L1 analyzer.

You give it `owner/repo` (or a github.com URL). It shallow-clones the repo, runs the static Slop Audit indicators over the source, and renders a one-card verdict: how much of the code is structurally capable of being exhaustively verified, driven by the mutable-state ratio (L1.18) and a handful of supporting signals.

It never executes the cloned repository's code. Only the static indicators run (`exec_tests=False`); the clone is shallow, single-branch, no-tags, and the working directory is deleted after every request. Decision-space *coverage* (L1.19) therefore shows `n/a`, honestly, because that number requires running the target's own test suite, which we do not do.

## Architecture

Honest Code all the way down:

- `app/config.py` is the only module that reads `os.environ`. Everything else takes `config: AppConfig` as a parameter.
- `app/logic/` is pure: `repo.parse_github_url` (a Maybe returning `RepoRef | None`) and `scorecard.build_scorecard` (results dict to view model). No I/O, no framework imports. Tested directly with `assert f(input) == expected`, no mocks.
- `app/services.py` holds the blocking I/O (git clone, analyzer invocation) behind typed `AuditError`.
- `app/routes/audit.py` is the boundary: extract form input, resolve the Maybe, run the I/O in a threadpool, map to a scorecard, return an HTMX fragment. The interior stays pure.
- `app/templates/` renders server-side HTML; HTMX swaps the result fragment in. No client-side state store.

## Run it

```bash
uv sync --extra dev
uv run pytest
uv run slop-audit-web        # or: uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000, paste `openhonest/slop-audit`, and read the card.

Config (all optional, read once at startup) lives in `.env`; see `.env.example`.
