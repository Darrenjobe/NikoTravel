"""GET /api/today — Morning Guide + Evening Recap for the current trip day."""
from __future__ import annotations

import json

from fastapi import APIRouter

import datetime as dt

from app.services import itinerary, tripday
from app.storage import db

router = APIRouter()

UPCOMING_DAYS = 2


@router.get("/api/today")
def today():
    ctx = tripday.context()
    out = {"trip_day": ctx["trip_day"], "date": ctx["date"], "region": ctx["region"],
           "morning_guide": None, "evening_recap": None,
           # Next couple of days, so the Home page can show what's coming
           # without a second round trip. Full trip: GET /api/itinerary.
           "upcoming": itinerary.days(
               start=dt.date.fromisoformat(ctx["date"]) + dt.timedelta(days=1),
               count=UPCOMING_DAYS,
           )}
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
