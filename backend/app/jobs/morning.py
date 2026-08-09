"""Morning Guide — researched briefing for today's itinerary region."""
from __future__ import annotations

import json

from app import config
from app.services import llm, search, tripday
from app.storage import db

GUIDE_SCHEMA = {
    "type": "object",
    "properties": {
        "stops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "hours": {"type": "string"},
                    "blurb": {"type": "string", "description": "2 sentences of history/context"},
                    "tip": {"type": "string", "description": "One practical tip"},
                },
                "required": ["name", "hours", "blurb", "tip"],
                "additionalProperties": False,
            },
        },
        "lunch": {"type": "string"},
    },
    "required": ["stops", "lunch"],
    "additionalProperties": False,
}


def run() -> dict:
    ctx = tripday.context()
    if not ctx["region"]:
        return {"skipped": "no itinerary region for today"}

    section = tripday.itinerary_section(ctx["region"])
    live = search.web_search(
        f"opening hours and visitor tips this week: top sites in {ctx['region']}, Greece"
    )
    guide = llm.get_llm().extract_json(
        model=config.JOB_MODEL,
        system=(
            "You are Niko, writing a morning travel guide for one traveler on a "
            "spiritual & historical tour of Greece. Pick the 3-4 best stops for "
            "today from their itinerary, in a sensible walking/driving order."
        ),
        prompt=(
            f"Today: {ctx['date']} (trip day {ctx['trip_day']}), region: {ctx['region']}.\n\n"
            f"Itinerary section:\n{section}\n\nLive info:\n{live}"
        ),
        schema=GUIDE_SCHEMA,
    )
    with db.conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO guides (day, kind, created_at, payload) VALUES (?,?,?,?)",
            (ctx["date"], "morning", db.now(), json.dumps(guide)),
        )
    return {"day": ctx["date"], "stops": len(guide["stops"])}
