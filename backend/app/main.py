"""Ὁδηγός (Hodegos) backend — FastAPI entry point.

App name: Ὁδηγός. "Nikos" is the in-app assistant persona and appears only in
prompts and user-facing assistant copy, never as an identifier.
"""
from __future__ import annotations

import logging
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request

from app import config
from app.routers import (
    admin,
    chat,
    conversations,
    events,
    itinerary,
    journal,
    journey,
    map as map_router,
    models,
    saved,
    today,
)
from app.storage import db

log = logging.getLogger("hodegos")


async def require_token(request: Request) -> None:
    if not config.API_TOKEN:
        raise HTTPException(
            503,
            "API_TOKEN is not set in the server's environment. Put it in "
            "backend/.env (generate one with `openssl rand -hex 32`) and "
            "restart uvicorn — see the startup log for what the server loaded.",
        )
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, config.API_TOKEN):
        # Diagnose in the server console only. The 401 body stays generic so
        # nothing about the expected token leaks to the network.
        if not auth:
            reason = "no Authorization header was sent"
        elif not auth.startswith("Bearer "):
            reason = f"header is not 'Bearer <token>' (got {auth.split(' ')[0]!r})"
        elif not token:
            reason = (
                "the Bearer token is empty — HodegosAPIToken is probably "
                "missing from the app's Info.plist"
            )
        else:
            reason = (
                f"token mismatch: client sent {len(token)} chars, "
                f"server expects {len(config.API_TOKEN)}"
            )
        log.warning("401 from %s — %s",
                    request.client.host if request.client else "unknown", reason)
        raise HTTPException(401, "invalid token")


app = FastAPI(title="Hodegos", docs_url=None, redoc_url=None)

for router in (chat.router, journal.router, today.router, journey.router,
               map_router.router, conversations.router, itinerary.router,
               events.router, saved.router, models.router, admin.router):
    app.include_router(router, dependencies=[Depends(require_token)])


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.on_event("startup")
def startup() -> None:
    db.init()
    _log_config()


def _log_config() -> None:
    """Print what the server actually loaded, so a misconfigured start is
    obvious in the console instead of surfacing later as a confusing 503.
    Booleans only — never log secret values."""
    env_file = config.BASE_DIR / ".env"
    checks = [
        ("API_TOKEN", bool(config.API_TOKEN)),
        ("ANTHROPIC_API_KEY", bool(os.environ.get("ANTHROPIC_API_KEY"))),
        ("GOOGLE_PLACES_API_KEY", bool(config.GOOGLE_PLACES_API_KEY)),
        ("TAVILY_API_KEY", bool(config.TAVILY_API_KEY)),
    ]
    log.warning("Ὁδηγός config — .env %s at %s",
                "found" if env_file.is_file() else "NOT FOUND", env_file)
    for name, present in checks:
        log.warning("  %s %s", "✓" if present else "✗", name)
    if not config.API_TOKEN:
        log.warning(
            "  → API_TOKEN missing: every authenticated route will return 503. "
            "Add it to %s and restart.", env_file)
