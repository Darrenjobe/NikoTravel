"""Map tab data — journaled pins and free-text place search."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import places
from app.storage import db

router = APIRouter()


@router.get("/api/map/pins")
def pins():
    with db.conn() as c:
        rows = c.execute(
            "SELECT id, place_name, lat, lon, sentiment, line, maps_url, category "
            "FROM journal_entries WHERE status='done' AND lat IS NOT NULL"
        ).fetchall()
    return {"pins": [dict(r) for r in rows]}


@router.get("/api/places/search")
def search(
    q: str = Query(min_length=1, description="Free text, e.g. 'taverna' or a name."),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    n: int = Query(default=10, ge=1, le=20),
):
    """Search Google Places from the Map tab.

    Deliberately the same `recommend()` the concierge uses, so a searched
    result and a recommended one are the same object — carrying the real
    Place ID and googleMapsUri that make "open the business page" and
    hearting possible. Client-side MapKit search can do neither.

    With no GOOGLE_PLACES_API_KEY this returns [] rather than erroring, matching
    how the rest of the app degrades; check the startup log if results are
    unexpectedly empty.
    """
    return {"places": places.recommend(q, lat, lon, n=n)}
