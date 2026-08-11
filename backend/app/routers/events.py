"""GET /api/events — nearby special events and celebrations."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import events as events_service

router = APIRouter()


@router.get("/api/events")
def get_events(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = Query(default=5.0, gt=0, le=100),
    refresh: bool = Query(default=False, description="Bypass the 12h cache"),
):
    return events_service.nearby(
        lat=lat, lon=lon, radius_km=radius_km, refresh=refresh
    )
