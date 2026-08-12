"""Saved (hearted) places — the Map tab's third pin layer.

A save is keyed on the Google Place ID, which is why map search has to come
from Google rather than MKLocalSearch: an Apple result has no stable ID to
heart. The full place payload is stored alongside the key so the saved layer
renders offline.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage import db

router = APIRouter()

FIELDS = (
    "place_id", "name", "address", "lat", "lon",
    "category", "rating", "rating_count", "maps_url", "note",
)


class SavedPlace(BaseModel):
    """Mirrors the place shape from services/places.py, so the client can POST
    back the same object it was given by search, chat, or a recommendation."""

    place_id: str
    name: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    category: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    maps_url: str | None = None
    note: str | None = None


@router.get("/api/saved")
def list_saved():
    with db.conn() as c:
        rows = c.execute(
            f"SELECT {', '.join(FIELDS)}, saved_at FROM saved_places "
            "ORDER BY saved_at DESC"
        ).fetchall()
    return {"places": [dict(r) for r in rows]}


@router.post("/api/saved")
def save_place(place: SavedPlace):
    """Heart a place. INSERT OR REPLACE so a double-tap is idempotent rather
    than a constraint error the client has to interpret."""
    if not place.place_id.strip():
        raise HTTPException(400, "place_id is required")
    values = [getattr(place, f) for f in FIELDS]
    with db.conn() as c:
        c.execute(
            f"INSERT OR REPLACE INTO saved_places ({', '.join(FIELDS)}, saved_at) "
            f"VALUES ({', '.join('?' * len(FIELDS))}, ?)",
            (*values, db.now()),
        )
    return {"ok": True, "saved": True, "place_id": place.place_id}


@router.delete("/api/saved/{place_id}")
def unsave_place(place_id: str):
    """Un-heart. Deleting something already gone is a success, not a 404 — the
    client's optimistic toggle can retry without special-casing the response."""
    with db.conn() as c:
        c.execute("DELETE FROM saved_places WHERE place_id=?", (place_id,))
    return {"ok": True, "saved": False, "place_id": place_id}
