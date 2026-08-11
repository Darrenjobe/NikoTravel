"""GET /api/itinerary — planned days and stops for the Home page."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Query

from app.services import itinerary, tripday

router = APIRouter()


@router.get("/api/itinerary")
def get_itinerary(
    days: int | None = Query(
        default=None, ge=1, le=30,
        description="How many days forward from `start`. Omit for the whole trip.",
    ),
    start: str | None = Query(
        default=None, description="ISO date (YYYY-MM-DD). Defaults to today."
    ),
):
    start_date: dt.date | None = None
    if start:
        try:
            start_date = dt.date.fromisoformat(start)
        except ValueError:
            start_date = None
    return {"days": itinerary.days(start=start_date, count=days)}
