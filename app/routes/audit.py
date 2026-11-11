"""
Audit boundary handlers.

Shape of the POST handler:
  1. Extract the form input.
  2. Resolve the Maybe from parse_github_url (None -> error partial).
  3. Do the clone + analyze I/O in a threadpool (both are blocking).
  4. Map results to a scorecard with a pure function.
  5. Return the HTMX fragment.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.copy import COPY
from app.logic.audit_log import build_audit_event
from app.logic.cache import cache_entry, cached_result
from app.logic.guards import evaluate_rate_limit
from app.logic.repo import parse_github_url
from app.logic.scorecard import build_scorecard
from app.services import (
    AuditError,
    analyze_config,
    analyze_repo,
    analyze_source,
    check_repo_size,
    clone_repo,
    log_audit_event,
)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
# All page prose lives in app/copy.md; expose it to every template as `copy`.
templates.env.globals["copy"] = COPY

# A short beat after each step so the narration is legible; the work itself is
# real and unpadded. Clone/parse already take real time; this only keeps the
# fast final steps from flashing past faster than a human can read them.
_STEP_BEAT_SECONDS = 0.35


# Errors (bad input, rate-limited, clone failure) must never be cached; a repo
# that fails now may succeed on retry. Successful scorecards are cacheable.
_NO_CACHE = {"Cache-Control": "no-store"}
_CACHE_1H = {"Cache-Control": "public, max-age=3600"}


def _error(request: Request, message: str) -> HTMLResponse:
    return templates.TemplateResponse(request, "audit/_error.html", {"message": message}, headers=_NO_CACHE)


def _render(name: str, context: dict[str, object]) -> str:
    return templates.get_template(name).render(context)


def _sse(event: str, payload: str) -> str:
    """One Server-Sent Event. The payload is JSON-encoded onto a single data
    line so multi-line HTML fragments survive without SSE framing pitfalls."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _client_key(request: Request) -> str:
    """Identify the caller for rate limiting. Behind Cloudflare/Render the socket
    peer is the proxy, so trust the forwarded client headers first."""
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(request: Request) -> bool:
    """Record this hit and report whether the caller is over the limit."""
    config = request.app.state.config
    store = request.app.state.rate_state
    key = _client_key(request)
    decision = evaluate_rate_limit(
        store.get(key, []),
        time.monotonic(),
        config["rate_limit_max_requests"],
        config["rate_limit_window_seconds"],
    )
    if decision["retained"]:
        store[key] = decision["retained"]
    else:
        store.pop(key, None)
    return not decision["allowed"]


def _elapsed_ms(started_at: float) -> float:
    return (time.monotonic() - started_at) * 1000


def _log_event(
    request: Request,
    *,
    endpoint: str,
    url: str,
    slug: str | None,
    outcome: str,
    cache_hit: bool,
    duration_ms: float | None,
    error: str | None,
) -> None:
    """Record one permanent audit-log line. See app/logic/audit_log.py and
    services.log_audit_event: a no-op until AUDIT_LOG_DIR points at a durable
    disk, never a failure the visitor's request can see."""
    event = build_audit_event(
        timestamp=datetime.now(UTC).isoformat(),
        endpoint=endpoint,
        client_key=_client_key(request),
        url=url,
        slug=slug,
        outcome=outcome,
        cache_hit=cache_hit,
        duration_ms=duration_ms,
        error=error,
    )
    log_audit_event(event, request.app.state.config)


# A real, captured audit of our own repo, shown on the landing page so a first-
# time visitor sees what the tool produces before typing anything. These are
# genuine measured values (openhonest/slop-audit), not fabricated illustration.
#
# Re-capture it when the analyzer's counting rules change, or the page shows numbers
# the live tool no longer produces. Captured 2026-08-14 against the analyzer at the
# commit this app pins, with:
#   uv run l1-analyzer <slop-audit> --no-exec --format json --lang python
_EXAMPLE_RESULTS: dict[str, object] = {
    "lang": "python",
    "L1.18": {"value": 0.0, "band": "Healthy", "details": "0/415 functions reference external mutable state (python)"},
    # Measured: slop-audit's own code carries no promiscuous or undetermined state
    # (pure functions, no instance state), so the meter ran and found nothing
    # unbounded. resolvable_fraction is a float, which is what marks the meter as
    # having actually run for this language.
    "L1.18b": {
        "verdict": "n/a",
        "counts": {"neutral": 0, "promiscuous": 0, "unresolved": 0},
        "resolvable_fraction": 1.0,
        "findings": [],
        "bucketed": {"counts": {"tests": 48, "vendored": 1966}, "paths": []},
    },
    "L1.19": {"value": 2017, "band": "n/a"},
    "path_cover": {"value": 930, "band": "n/a", "functions": 415},
    "L1.15": {"value": 0.0, "band": "Healthy", "details": "0 escapes in ~9kLOC"},
    "L1.17": {"value": 0.0, "band": "Healthy"},
    "L1.16": {"value": 0.0, "band": "Healthy"},
    "L1.10": {"value": 5, "band": "Healthy"},
    "L1.11": {"value": "present and parameterized", "band": "Healthy"},
    "L1.9": {"value": "present", "band": "Healthy"},
    # Measured: slop-audit's own code is pure-functional, imports no threading, and
    # keeps no module-level mutable containers, so the concurrency surface is empty.
    "thread_surface": {"verdict": "clean", "value": "0 exposed / 0 review / 0 candidate", "band": "n/a",
                       "counts": {"exposed": 0, "review": 0, "candidate": 0}, "findings": [],
                       "bucketed": {"counts": {}, "paths": []}},
}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    example = build_scorecard("openhonest/slop-audit", "python", _EXAMPLE_RESULTS)
    return templates.TemplateResponse(request, "index.html", {"example": example})


@router.get("/audit", response_class=HTMLResponse)
async def audit(request: Request, url: str = Query(...)):
    # GET (not POST) so Cloudflare can edge-cache results by ?url=. The endpoint
    # has no user side effects: it clones to a temp dir and deletes it. Repeated
    # audits of the same repo are served from Cloudflare's edge cache here, and
    # from the process-local result cache on a direct origin hit or from
    # /audit/stream; the origin only clones on a genuine cache miss, which is
    # where the rate-limit backstop and clone timeout bite.
    config = request.app.state.config
    started_at = time.monotonic()

    if _rate_limited(request):
        _log_event(request, endpoint="audit", url=url, slug=None, outcome="rate_limited",
                   cache_hit=False, duration_ms=None, error=None)
        return _error(request, "Too many audits from your network just now. Give it a minute and try again.")

    ref = parse_github_url(url)
    if ref is None:
        _log_event(request, endpoint="audit", url=url, slug=None, outcome="bad_url",
                   cache_hit=False, duration_ms=None, error=None)
        return _error(request, "That doesn't look like a GitHub repository. Try owner/repo or a github.com URL.")

    hit = cached_result(request.app.state.result_cache, ref["slug"], time.monotonic())
    if hit is not None:
        lang, results = hit
        card = build_scorecard(ref["slug"], lang, results)
        _log_event(request, endpoint="audit", url=url, slug=ref["slug"], outcome="success",
                   cache_hit=True, duration_ms=_elapsed_ms(started_at), error=None)
        return templates.TemplateResponse(request, "audit/_scorecard.html", {"card": card}, headers=_CACHE_1H)

    work_dir = Path(config["work_dir"])
    work_dir.mkdir(parents=True, exist_ok=True)
    dest = work_dir / f"{ref['owner']}-{ref['name']}-{uuid.uuid4().hex[:8]}"

    try:
        await run_in_threadpool(check_repo_size, ref["slug"], config)
        await run_in_threadpool(clone_repo, ref["clone_url"], dest, config)
        lang, results = await run_in_threadpool(analyze_repo, dest, config)
    except AuditError as error:
        _log_event(request, endpoint="audit", url=url, slug=ref["slug"], outcome="error",
                   cache_hit=False, duration_ms=_elapsed_ms(started_at), error=str(error))
        return _error(request, str(error))
    finally:
        shutil.rmtree(dest, ignore_errors=True)

    request.app.state.result_cache[ref["slug"]] = cache_entry(
        lang, results, time.monotonic(), config["result_cache_ttl_seconds"]
    )
    card = build_scorecard(ref["slug"], lang, results)
    _log_event(request, endpoint="audit", url=url, slug=ref["slug"], outcome="success",
               cache_hit=False, duration_ms=_elapsed_ms(started_at), error=None)
    return templates.TemplateResponse(request, "audit/_scorecard.html", {"card": card}, headers=_CACHE_1H)


@router.get("/audit/stream")
async def audit_stream(request: Request, url: str = Query(...)) -> StreamingResponse:
    """The same audit as GET /audit, but narrated. Each step is emitted right
    before the server actually does that work, so the progress is real, not a
    canned animation. Not cacheable at the edge (it streams); /audit is the
    cacheable twin used for shares and permalinks. This is the path real
    visitors use, though, so it shares the process-local result cache with
    /audit: without that, every narrated run re-cloned its target regardless
    of how recently the same repo had just been audited."""
    started_at = time.monotonic()

    async def gen() -> AsyncIterator[str]:
        if _rate_limited(request):
            _log_event(request, endpoint="audit_stream", url=url, slug=None, outcome="rate_limited",
                       cache_hit=False, duration_ms=None, error=None)
            yield _sse("fail", _render("audit/_error.html",
                {"request": request, "message": "Too many audits from your network just now. Give it a minute."}))
            return
        ref = parse_github_url(url)
        if ref is None:
            _log_event(request, endpoint="audit_stream", url=url, slug=None, outcome="bad_url",
                       cache_hit=False, duration_ms=None, error=None)
            yield _sse("fail", _render("audit/_error.html",
                {"request": request, "message": "That doesn't look like a GitHub repository. Try owner/repo or a github.com URL."}))
            return

        config = request.app.state.config

        hit = cached_result(request.app.state.result_cache, ref["slug"], time.monotonic())
        if hit is not None:
            lang, results = hit
            yield _sse("step", f"Found a recent audit of {ref['slug']} — reusing it instead of re-cloning…")
            await asyncio.sleep(_STEP_BEAT_SECONDS)
            card = build_scorecard(ref["slug"], lang, results)
            _log_event(request, endpoint="audit_stream", url=url, slug=ref["slug"], outcome="success",
                       cache_hit=True, duration_ms=_elapsed_ms(started_at), error=None)
            yield _sse("done", _render("audit/_scorecard.html", {"request": request, "card": card}))
            return

        work_dir = Path(config["work_dir"])
        work_dir.mkdir(parents=True, exist_ok=True)
        dest = work_dir / f"{ref['owner']}-{ref['name']}-{uuid.uuid4().hex[:8]}"
        try:
            yield _sse("step", f"Looking up {ref['slug']} on GitHub…")
            await run_in_threadpool(check_repo_size, ref["slug"], config)
            await asyncio.sleep(_STEP_BEAT_SECONDS)

            yield _sse("step", f"Cloning {ref['slug']} — a shallow copy, no history…")
            await run_in_threadpool(clone_repo, ref["clone_url"], dest, config)

            yield _sse("step", "Parsing the source into abstract syntax trees…")
            source = await run_in_threadpool(analyze_source, dest, config)

            yield _sse("step", "Inspecting CI, containers, and commit discipline…")
            config_results = await run_in_threadpool(analyze_config, dest)
            await asyncio.sleep(_STEP_BEAT_SECONDS)

            yield _sse("step", "Scoring verifiability and mapping to the audit dimensions…")
            results = {**config_results, **source}
            lang = str(results.get("lang", "unknown"))
            request.app.state.result_cache[ref["slug"]] = cache_entry(
                lang, results, time.monotonic(), config["result_cache_ttl_seconds"]
            )
            card = build_scorecard(ref["slug"], lang, results)
            await asyncio.sleep(_STEP_BEAT_SECONDS)

            _log_event(request, endpoint="audit_stream", url=url, slug=ref["slug"], outcome="success",
                       cache_hit=False, duration_ms=_elapsed_ms(started_at), error=None)
            yield _sse("done", _render("audit/_scorecard.html", {"request": request, "card": card}))
        except AuditError as error:
            _log_event(request, endpoint="audit_stream", url=url, slug=ref["slug"], outcome="error",
                       cache_hit=False, duration_ms=_elapsed_ms(started_at), error=str(error))
            yield _sse("fail", _render("audit/_error.html", {"request": request, "message": str(error)}))
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    headers = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)
