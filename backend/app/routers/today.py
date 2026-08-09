"""GET /api/today — Morning Guide + Evening Recap for the current trip day."""
from __future__ import annotations

import json

from fastapi import APIRouter

from app.services import tripday
from app.storage import db

router = APIRouter()


@router.get("/api/today")
def today():
    ctx = tripday.context()
    out = {"trip_day": ctx["trip_day"], "date": ctx["date"], "region": ctx["region"],
           "morning_guide": None, "evening_recap": None}
    with db.conn() as c:
        for kind in ("morning", "evening"):
            row = c.execute(
                "SELECT payload FROM guides WHERE day=? AND kind=?", (ctx["date"], kind)
            ).fetchone()
            if row:
                out[f"{kind}_guide" if kind == "morning" else "evening_recap"] = json.loads(
                    row["payload"]
                )
    return out
