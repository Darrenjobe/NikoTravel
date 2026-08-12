"""Model selection — list what's available and change what the app runs on.

Lets the phone switch models mid-trip: drop to a cheaper model when spend
looks high, or move back up for a hard question, without a redeploy or a
dashboard. Chat and jobs are set independently because they have different
constraints — chat is latency-sensitive on the ground, jobs run overnight.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app import config
from app.services import models as model_catalog
from app.services import settings

router = APIRouter()

ROLES = {"chat_model": settings.chat_model, "job_model": settings.job_model}


class ModelSelection(BaseModel):
    """Both optional — send only the role you're changing."""

    chat_model: str | None = None
    job_model: str | None = None


def _current() -> dict:
    return {
        "chat_model": settings.chat_model(),
        "job_model": settings.job_model(),
        "defaults": {"chat_model": config.CHAT_MODEL, "job_model": config.JOB_MODEL},
        "provider": config.LLM_PROVIDER,
    }


@router.get("/api/models")
def list_models(
    refresh: bool = Query(
        default=False, description="Bypass the 24h cache and re-ask Anthropic."
    ),
    all: bool = Query(
        default=False, description="Include models this app can't run on."
    ),
):
    result = model_catalog.catalog(refresh=refresh)
    models = result["models"]
    if not all:
        # A model without structured outputs breaks journal extraction, so
        # hiding it from the picker is the point — `all=true` is for debugging.
        hidden = [m for m in models if m.get("compatible") is False]
        models = [m for m in models if m.get("compatible") is not False]
        result["hidden_incompatible"] = len(hidden)
    return {**result, "models": models, **_current()}


@router.get("/api/models/current")
def current_models():
    """Just the selection — no network call, no catalog."""
    return _current()


@router.post("/api/models")
def set_models(selection: ModelSelection):
    """Change the model for chat, jobs, or both.

    Validated against the catalog when we have live data. When the catalog is
    only a fallback we accept the value anyway and say so: refusing to change
    models because the *listing* call failed would be the wrong failure mode
    on a bad connection, which is exactly when you want a cheaper model.
    """
    requested = {k: v for k, v in selection.model_dump().items() if v is not None}
    if not requested:
        raise HTTPException(400, f"Send at least one of {sorted(ROLES)}")

    for role, value in requested.items():
        if not value.strip():
            raise HTTPException(400, f"{role} cannot be blank")

    result = model_catalog.catalog()
    verified = result["source"] in ("live", "cache", "stale-cache")
    known = model_catalog.known_ids(result["models"])
    warnings = []

    for role, value in requested.items():
        if verified and value not in known:
            raise HTTPException(
                400,
                f"unknown model: {value}. Available: {sorted(known)}",
            )
        if not verified:
            warnings.append(
                f"{value} was not verified — the model catalog is unavailable "
                f"({result.get('note', 'no detail')})."
            )
        settings.set(role, value)

    return {"ok": True, **_current(), "warnings": warnings}


@router.delete("/api/models")
def reset_models():
    """Drop the overrides and fall back to the env-var defaults."""
    for role in ROLES:
        settings.clear(role)
    return {"ok": True, **_current()}
