"""Assembles the ambient context block injected into every AI prompt.

The traveler shouldn't have to tell Nikos where they are, what day it is, or
what they've already thought about a place. The client sends lat/lon and a
timestamp on every request; everything else is derived server-side from the
itinerary and the journal.
"""
from __future__ import annotations

import datetime as dt
import zoneinfo

from app import config
from app.services import itinerary, tripday
from app.storage import db


def _parse_client_time(timestamp: str | None) -> dt.datetime:
    """Prefer the phone's clock (it knows the real local offset); fall back to
    server time in the trip timezone."""
    tz = zoneinfo.ZoneInfo(config.TRIP_TZ)
    if timestamp:
        try:
            parsed = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=tz)
        except ValueError:
            pass
    return dt.datetime.now(tz)


def _recent_journal(limit: int = 5) -> list[dict]:
    with db.conn() as c:
        rows = c.execute(
            "SELECT place_name, sentiment, line FROM journal_entries "
            "WHERE status='done' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def _preferences() -> dict:
    with db.conn() as c:
        rows = c.execute("SELECT kind, label FROM preferences").fetchall()
    return {
        "likes": [r["label"] for r in rows if r["kind"] == "like"],
        "dislikes": [r["label"] for r in rows if r["kind"] == "dislike"],
    }


def build(
    lat: float | None = None,
    lon: float | None = None,
    timestamp: str | None = None,
    include_journal: bool = True,
) -> str:
    """Natural-language context block for the system prompt."""
    now = _parse_client_time(timestamp)
    ctx = tripday.context(now.date())
    parts: list[str] = []

    # --- Where and when -------------------------------------------------
    where = ctx["region"] or "an unscheduled location"
    if lat is not None and lon is not None:
        where += f" (currently at {lat:.4f}, {lon:.4f})"
    when = now.strftime("%-I:%M %p on %A, %-d %B %Y")
    if ctx["trip_day"]:
        # Derived, not hardcoded: a fixed "21-day trip" was correct only for
        # the Greece itinerary and silently lied about any other one — telling
        # the model day 1 of 21 on a five-day test trip, which changes how it
        # paces advice.
        schedule = tripday.schedule()
        total = (
            (max(r["end"] for r in schedule) - min(r["start"] for r in schedule)).days + 1
            if schedule else None
        )
        length = f" of a {total}-day trip" if total else ""
        parts.append(
            f"The traveler is in {where}. Local time is {when} — "
            f"day {ctx['trip_day']}{length}."
        )
    else:
        parts.append(
            f"The trip has not started yet. Local time is {when}. "
            f"Planned first region: {where}."
        )

    # --- Today's plan ---------------------------------------------------
    today_days = itinerary.days(start=now.date(), count=1)
    if today_days and today_days[0]["stops"]:
        names = ", ".join(s["name"] for s in today_days[0]["stops"][:8])
        parts.append(f"Planned sites in this region: {names}.")
        dining = today_days[0]["dining"]
        if dining:
            picks = "; ".join(
                f"{d['meal']}: {', '.join(d['options'][:2])}" for d in dining
            )
            parts.append(f"Itinerary dining options — {picks}.")

    # --- Tomorrow -------------------------------------------------------
    ahead = itinerary.days(start=now.date() + dt.timedelta(days=1), count=1)
    if ahead and ahead[0]["region"] != ctx["region"]:
        parts.append(
            f"Tomorrow they move to {ahead[0]['region']} — factor that into "
            "any advice about timing, packing, or last chances."
        )

    # --- What they already think ----------------------------------------
    if include_journal:
        prefs = _preferences()
        if prefs["likes"] or prefs["dislikes"]:
            bits = []
            if prefs["likes"]:
                bits.append("likes " + ", ".join(prefs["likes"][:8]))
            if prefs["dislikes"]:
                bits.append("dislikes " + ", ".join(prefs["dislikes"][:8]))
            parts.append("Known preferences: " + "; ".join(bits) + ".")

        recent = _recent_journal()
        if recent:
            lines = "; ".join(
                f"{r['place_name'] or 'an unconfirmed place'} ({r['sentiment']}) — {r['line']}"
                for r in recent
                if r["line"]
            )
            if lines:
                parts.append(f"Recently journaled: {lines}.")

    return "\n".join(f"- {p}" for p in parts)
