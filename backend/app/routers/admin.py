"""Admin: knowledge re-indexing and manual/cron job triggers."""
from __future__ import annotations

import inspect

from fastapi import APIRouter, HTTPException, Query

from app import config
from app.jobs import evening, insights, morning, summarize
from app.services import itinerary, rag, tripday

router = APIRouter()

JOBS = {
    "morning": morning.run,
    "evening": evening.run,
    "insights": insights.run,
    "summarize": summarize.run,
}


@router.post("/api/rebuild-index")
def rebuild_index():
    """Re-read everything in knowledge/ after editing it.

    Two things go stale on an edit, so both are refreshed here: the Chroma
    index the concierge retrieves from, and the in-process caches holding the
    parsed schedule and per-region stops. Clearing only the first would leave
    /api/today and /api/itinerary serving the old itinerary until a restart.
    """
    tripday.clear_cache()
    itinerary.clear_cache()
    count = rag.rebuild_knowledge()
    files = sorted(
        str(p.relative_to(config.KNOWLEDGE_DIR))
        for p in config.KNOWLEDGE_DIR.rglob("*.md")
    )
    return {
        "indexed_chunks": count,
        "files": files,
        "itinerary_file": str(config.ITINERARY_FILE),
        "itinerary_found": config.ITINERARY_FILE.is_file(),
        "trip_days_parsed": len(itinerary.days()),
    }


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
