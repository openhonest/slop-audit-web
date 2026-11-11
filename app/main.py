"""
FastAPI entry point for the hosted Slop Audit.

Stateless: no database, no auth. Lifespan loads config once and stashes it on
app.state.config; every handler reads config from there, no hidden env reads.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import load_config
from app.routes import audit
from app.services import sweep_work_dir

load_dotenv()

logger = logging.getLogger("slop_audit.main")


async def _sweep_loop(app: FastAPI) -> None:
    """Catch orphaned work-dir entries a crashed request leaves behind between
    the startup sweep and the next restart."""
    config = app.state.config
    work_dir = Path(config["work_dir"])
    while True:
        await asyncio.sleep(config["work_dir_sweep_interval_seconds"])
        removed = sweep_work_dir(work_dir, config["work_dir_max_age_seconds"])
        if removed:
            logger.info("swept %d orphaned work dirs: %s", len(removed), removed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config()
    # Per-client hit history for the origin rate-limit backstop. Cloudflare does
    # the real edge limiting; this bounds direct hits on the .onrender.com origin.
    app.state.rate_state = {}
    # Cloned-and-analyzed results, keyed by repo slug, shared by /audit and
    # /audit/stream so a repeat audit reuses the last clone instead of paying
    # for a fresh one. See app/logic/cache.py.
    app.state.result_cache = {}

    config = app.state.config
    removed = sweep_work_dir(Path(config["work_dir"]), config["work_dir_max_age_seconds"])
    if removed:
        logger.info("startup sweep removed %d orphaned work dirs: %s", len(removed), removed)
    sweep_task = asyncio.create_task(_sweep_loop(app))

    yield

    sweep_task.cancel()


app = FastAPI(lifespan=lifespan, title="Slop Audit")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(audit.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
