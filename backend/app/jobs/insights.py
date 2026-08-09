"""Insights digest — mine the trailing 24h of interactions for trend cards.

Runs only when there's enough signal (2+ user interactions in the window),
matching the product rule: no activity, no digest.
"""
from __future__ import annotations

from app import config
from app.services import archive, llm
from app.storage import db

INSIGHTS_SCHEMA = {
    "type": "object",
    "properties": {
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "emoji": {"type": "string"},
                    "text": {"type": "string", "description": "One interesting fact or trend, 1-2 sentences, second person"},
                },
                "required": ["emoji", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["insights"],
    "additionalProperties": False,
}


def run() -> dict:
    n = archive.interactions_last_hours(24)
    if n < 2:
        return {"skipped": f"only {n} interactions in the last 24h"}

    window = archive.window_text(24)
    result = llm.get_llm().extract_json(
        model=config.JOB_MODEL,
        system=(
            "You analyze one traveler's day of interactions (questions to their "
            "concierge, journal entries, conversations) and surface 2-4 genuinely "
            "interesting facts or trends — counts, patterns, streaks, firsts. "
            "Concrete and specific beats generic; skip anything you can't ground "
            "in the transcript."
        ),
        prompt=window,
        schema=INSIGHTS_SCHEMA,
    )
    import datetime as dt

    tag = dt.date.today().strftime("%b %-d") + " · digest"
    with db.conn() as c:
        for item in result["insights"]:
            c.execute(
                "INSERT INTO insights (id, created_at, emoji, text, tag) VALUES (?,?,?,?,?)",
                (db.new_id(), db.now(), item["emoji"], item["text"], tag),
            )
    return {"generated": len(result["insights"])}
