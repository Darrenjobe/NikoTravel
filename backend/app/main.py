"""Ὁδηγός (Hodegos) backend — FastAPI entry point.

App name: Ὁδηγός. "Niko" is the in-app assistant persona and appears only in
prompts and user-facing assistant copy, never as an identifier.
"""
from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, HTTPException, Request

from app import config
from app.routers import admin, chat, journal, journey, map as map_router, today
from app.storage import db


async def require_token(request: Request) -> None:
    if not config.API_TOKEN:
        raise HTTPException(503, "API_TOKEN is not configured on the server")
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, config.API_TOKEN):
        raise HTTPException(401, "invalid token")


app = FastAPI(title="Hodegos", docs_url=None, redoc_url=None)

for router in (chat.router, journal.router, today.router, journey.router,
               map_router.router, admin.router):
    app.include_router(router, dependencies=[Depends(require_token)])


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.on_event("startup")
def startup() -> None:
    db.init()
