"""Admin: knowledge re-indexing and manual/cron job triggers."""
from __future__ import annotations

import inspect

from fastapi import APIRouter, HTTPException, Query

from app.jobs import evening, insights, morning, summarize
from app.services import rag

router = APIRouter()

JOBS = {
    "morning": morning.run,
    "evening": evening.run,
    "insights": insights.run,
    "summarize": summarize.run,
}


@router.post("/api/rebuild-index")
def rebuild_index():
    count = rag.rebuild_knowledge()
    return {"indexed_chunks": count}


@router.post("/api/jobs/{name}")
def run_job(
    name: str,
    force: bool = Query(
        default=False,
        description="Bypass a job's activity/idle threshold (testing).",
    ),
    hours: int | None = Query(
        default=None, ge=1, le=720,
        description="Override the lookback window, where the job has one.",
    ),
    limit: int | None = Query(default=None, ge=1, le=100),
):
    """Run a job on demand.

    Render's cron services call this with no parameters; the overrides exist
    so the same jobs can be exercised locally against a thin archive without
    waiting for thresholds to be met. Each is passed only to jobs whose
    signature accepts it, so adding a job needs no changes here.
    """
    if name not in JOBS:
        raise HTTPException(404, f"unknown job: {name}. Try one of {sorted(JOBS)}")
    fn = JOBS[name]
    accepted = inspect.signature(fn).parameters
    kwargs = {}
    for key, value in (("force", force), ("hours", hours), ("limit", limit)):
        if key in accepted and value is not None:
            kwargs[key] = value
    return fn(**kwargs)
