"""
FastAPI entry point for the hosted Slop Audit.

Stateless: no database, no auth. Lifespan loads config once and stashes it on
app.state.config; every handler reads config from there, no hidden env reads.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import load_config
from app.routes import audit

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config()
    # Per-client hit history for the origin rate-limit backstop. Cloudflare does
    # the real edge limiting; this bounds direct hits on the .onrender.com origin.
    app.state.rate_state = {}
    yield


app = FastAPI(lifespan=lifespan, title="Slop Audit")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(audit.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
