"""Insights digest — mine the trailing 24h of interactions for trend cards.

Runs only when there's enough signal (2+ user interactions in the window),
matching the product rule: no activity, no digest.
"""
from __future__ import annotations

from app import config
from app.services import archive, llm, settings, tripday
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


MIN_INTERACTIONS = 2


def run(hours: int = 24, force: bool = False) -> dict:
    """Generate insight cards from the trailing `hours` of interactions.

    `force` skips the activity threshold (useful when testing locally with a
    thin archive); `hours` widens the window. Neither is used in production —
    the cron job calls this with defaults.
    """
    n = archive.interactions_last_hours(hours)
    if n < MIN_INTERACTIONS and not force:
        return {
            "skipped": f"only {n} interaction(s) in the last {hours}h "
                       f"(need {MIN_INTERACTIONS}); retry with ?force=true"
        }

    window = archive.window_text(hours)
    if not window.strip():
        # Forcing past the threshold still can't invent material to analyze.
        return {"skipped": f"no interactions recorded in the last {hours}h"}
    result = llm.get_llm().extract_json(
        model=settings.job_model(),
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

    # Trip-timezone date, not the server's UTC date.
    tag = tripday.today().strftime("%b %-d") + " · digest"
    with db.conn() as c:
        for item in result["insights"]:
            c.execute(
                "INSERT INTO insights (id, created_at, emoji, text, tag) VALUES (?,?,?,?,?)",
                (db.new_id(), db.now(), item["emoji"], item["text"], tag),
            )
    return {"generated": len(result["insights"])}
