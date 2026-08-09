"""GET /api/map/pins — journaled places with coordinates for the Map tab."""
from __future__ import annotations

from fastapi import APIRouter

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
