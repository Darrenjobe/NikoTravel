"""Structured reads of the itinerary Markdown.

`tripday` answers "which region am I in on date X". This module answers "what
is actually *at* that region" by parsing the destination profiles — the
`* **Name:** description` bullets under "Key Sites & Activities" and the
dining tables. Everything is derived from knowledge/, so the itinerary file
stays the single source of truth.
"""
from __future__ import annotations

import datetime as dt
import re
from functools import lru_cache

from app import config
from app.services import tripday

_BULLET = re.compile(r"^\*\s+\*\*(?P<name>[^:*]+):?\*\*:?\s*(?P<blurb>.*)$")


@lru_cache(maxsize=32)
def sites_for_region(region: str | None) -> list[dict]:
    """Parse the 'Key Sites & Activities' bullets for a region."""
    section = tripday.itinerary_section(region)
    if not section:
        return []
    # Narrow to the sites subsection so dining bullets don't leak in.
    match = re.search(
        r"### Key Sites & Activities\s*(.*?)(?=^###|\Z)", section, re.S | re.M
    )
    body = match.group(1) if match else section
    sites = []
    for line in body.splitlines():
        m = _BULLET.match(line.strip())
        if m:
            sites.append(
                {
                    "name": m.group("name").strip(),
                    "blurb": m.group("blurb").strip(),
                }
            )
    return sites


@lru_cache(maxsize=32)
def dining_for_region(region: str | None) -> list[dict]:
    """Parse the dining table rows into {meal, options[]}."""
    section = tripday.itinerary_section(region)
    if not section:
        return []
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].startswith("**"):
            meal = cells[0].strip("*").rstrip(":")
            options = [c for c in cells[1:] if c and c != "-"]
            rows.append({"meal": meal, "options": options})
    return rows


def days(start: dt.date | None = None, count: int | None = None) -> list[dict]:
    """Trip days with their region and planned sites.

    `start` defaults to today; `count` limits how many days forward. With no
    arguments, returns the whole trip.
    """
    schedule = tripday.schedule()
    if not schedule:
        return []
    trip_start = min(r["start"] for r in schedule)
    trip_end = max(r["end"] for r in schedule)

    first = start or tripday.today()
    first = max(first, trip_start)

    out = []
    day = first
    while day <= trip_end and (count is None or len(out) < count):
        region = next(
            (r["region"] for r in schedule if r["start"] <= day <= r["end"]), None
        )
        if region:
            out.append(
                {
                    "date": day.isoformat(),
                    "trip_day": (day - trip_start).days + 1,
                    "region": region,
                    "stops": sites_for_region(region),
                    "dining": dining_for_region(region),
                }
            )
        day += dt.timedelta(days=1)
    return out
