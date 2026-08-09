"""Admin: knowledge re-indexing and manual/cron job triggers."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.jobs import evening, insights, morning
from app.services import rag

router = APIRouter()

JOBS = {"morning": morning.run, "evening": evening.run, "insights": insights.run}


@router.post("/api/rebuild-index")
def rebuild_index():
    count = rag.rebuild_knowledge()
    return {"indexed_chunks": count}


@router.post("/api/jobs/{name}")
def run_job(name: str):
    if name not in JOBS:
        raise HTTPException(404, f"unknown job: {name}")
    return JOBS[name]()
