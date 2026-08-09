"""GET /api/places, GET /api/insights — the Journey tab."""
from __future__ import annotations

from fastapi import APIRouter

from app.storage import db

router = APIRouter()


@router.get("/api/places")
def list_places():
    with db.conn() as c:
        rows = c.execute(
            "SELECT * FROM journal_entries WHERE status='done' ORDER BY created_at DESC"
        ).fetchall()
        prefs = c.execute("SELECT kind, label FROM preferences ORDER BY updated_at DESC").fetchall()
    return {
        "entries": [db.row_to_dict(r) for r in rows],
        "preferences": {
            "likes": [p["label"] for p in prefs if p["kind"] == "like"],
            "dislikes": [p["label"] for p in prefs if p["kind"] == "dislike"],
        },
    }


@router.get("/api/insights")
def list_insights():
    with db.conn() as c:
        rows = c.execute(
            "SELECT * FROM insights ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return {"insights": [dict(r) for r in rows]}
