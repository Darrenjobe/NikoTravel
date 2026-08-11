"""Nearby events and celebrations.

There's no single reliable events API for rural Greece, so this uses the
search tool already wired up and has the LLM extract structure. Results are
cached per (date, region) in the `guides` table — one search per day per
region rather than one per app launch, which keeps the free Tavily tier
comfortable.
"""
from __future__ import annotations

import datetime as dt
import json
import logging

from app import config
from app.services import llm, search, tripday
from app.storage import db

log = logging.getLogger("hodegos")

CACHE_TTL = 12 * 3600

EVENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD, or '' if unclear"},
                    "time": {"type": "string", "description": "HH:MM local, or '' if unclear"},
                    "location": {"type": "string"},
                    "blurb": {"type": "string", "description": "One sentence"},
                    "url": {"type": "string", "description": "Source URL, or ''"},
                },
                "required": ["title", "date", "time", "location", "blurb", "url"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["events"],
    "additionalProperties": False,
}

SYSTEM = (
    "Extract genuine, time-specific local events from these search results: "
    "festivals, saint's days, concerts, markets, religious celebrations. "
    "Only include events you can actually place on a date near the traveler — "
    "discard generic tourist-attraction listings, permanent exhibits, and "
    "anything without a real date. Returning an empty list is correct when "
    "nothing qualifies; never invent an event."
)


def _cache_key(day: str, region: str | None) -> str:
    return f"events:{region or 'unknown'}"


def _cached(day: str, region: str | None) -> list[dict] | None:
    with db.conn() as c:
        row = c.execute(
            "SELECT created_at, payload FROM guides WHERE day=? AND kind=?",
            (day, _cache_key(day, region)),
        ).fetchone()
    if row and db.now() - row["created_at"] < CACHE_TTL:
        return json.loads(row["payload"])["events"]
    return None


def _store(day: str, region: str | None, events: list[dict]) -> None:
    with db.conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO guides (day, kind, created_at, payload) VALUES (?,?,?,?)",
            (day, _cache_key(day, region), db.now(), json.dumps({"events": events})),
        )


def nearby(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 5.0,
    refresh: bool = False,
) -> dict:
    ctx = tripday.context()
    day, region = ctx["date"], ctx["region"]

    if not refresh:
        cached = _cached(day, region)
        if cached is not None:
            return {"events": cached, "region": region, "cached": True}

    if not config.TAVILY_API_KEY:
        return {"events": [], "region": region, "cached": False,
                "note": "web search is not configured"}

    where = region or (f"{lat:.3f},{lon:.3f}" if lat is not None else "Greece")
    results = search.web_search(
        f"local events festivals saint's day celebrations near {where} Greece "
        f"on {day} and the following days",
        max_results=6,
    )
    try:
        parsed = llm.get_llm().extract_json(
            model=config.JOB_MODEL,
            system=SYSTEM,
            prompt=f"Traveler is near {where}. Today is {day}.\n\n{results}",
            schema=EVENTS_SCHEMA,
        )
        events = parsed["events"]
    except Exception as exc:
        log.warning("events extraction failed: %s", exc)
        return {"events": [], "region": region, "cached": False,
                "note": "could not read events right now"}

    _store(day, region, events)
    return {"events": events, "region": region, "cached": False}
