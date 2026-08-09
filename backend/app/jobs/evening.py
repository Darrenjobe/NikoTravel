"""Evening Recap — compile today's journal entries into a daily summary."""
from __future__ import annotations

import datetime as dt
import json
import zoneinfo

from app import config
from app.services import llm, tripday
from app.storage import db


def run() -> dict:
    ctx = tripday.context()
    tz = zoneinfo.ZoneInfo(config.TRIP_TZ)
    day_start = dt.datetime.fromisoformat(ctx["date"]).replace(tzinfo=tz).timestamp()

    with db.conn() as c:
        rows = c.execute(
            "SELECT place_name, sentiment, line, summary, maps_url FROM journal_entries "
            "WHERE status='done' AND created_at >= ? ORDER BY created_at",
            (day_start,),
        ).fetchall()

    entries = [dict(r) for r in rows]
    if not entries:
        return {"skipped": "no journal entries today"}

    narrative = llm.get_llm().complete(
        model=config.JOB_MODEL,
        system="Write a warm 2-3 sentence recap of this traveler's day from their journal summaries.",
        prompt=json.dumps(entries),
        max_tokens=400,
    )
    payload = {"narrative": narrative, "entries": entries}
    with db.conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO guides (day, kind, created_at, payload) VALUES (?,?,?,?)",
            (ctx["date"], "evening", db.now(), json.dumps(payload)),
        )
    return {"day": ctx["date"], "entries": len(entries)}
