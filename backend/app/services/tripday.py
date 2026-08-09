"""Date → trip day/region mapping, parsed from the itinerary's overview table.

Table rows look like: | Athens (Start) & Daytrip to Patmos | 3 Days | Sept 5-7 |
"""
from __future__ import annotations

import datetime as dt
import re
import zoneinfo
from functools import lru_cache

from app import config

MONTHS = {m.lower()[:4].rstrip("."): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def _parse_dates(text: str) -> tuple[dt.date, dt.date] | None:
    # Handles "Sept 5-7", "Sept 13-14", "Sept 15", "Sept 17 (Afternoon) - 19", "Sept 24-25"
    m = re.search(r"([A-Za-z]+)\.?\s+(\d+)(?:.*?[-–]\s*(?:[A-Za-z]+\.?\s+)?(\d+))?", text)
    if not m:
        return None
    month = MONTHS.get(m.group(1).lower()[:4])
    if not month:
        return None
    start = dt.date(config.TRIP_YEAR, month, int(m.group(2)))
    end = dt.date(config.TRIP_YEAR, month, int(m.group(3))) if m.group(3) else start
    return start, end


@lru_cache(maxsize=1)
def schedule() -> list[dict]:
    rows = []
    if not config.ITINERARY_FILE.exists():
        return rows
    for line in config.ITINERARY_FILE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and not cells[0].startswith("-") and "Region" not in cells[0]:
            dates = _parse_dates(cells[2])
            if dates:
                rows.append({"region": cells[0], "start": dates[0], "end": dates[1]})
    return rows


def today() -> dt.date:
    tz = zoneinfo.ZoneInfo(config.TRIP_TZ)
    return dt.datetime.now(tz).date()


def context(day: dt.date | None = None) -> dict:
    day = day or today()
    trip_start = min((r["start"] for r in schedule()), default=None)
    trip_day = (day - trip_start).days + 1 if trip_start else None
    region = next(
        (r["region"] for r in schedule() if r["start"] <= day <= r["end"]), None
    )
    return {
        "date": day.isoformat(),
        "trip_day": trip_day if trip_day and trip_day > 0 else None,
        "region": region,
    }


def itinerary_section(region: str | None) -> str:
    """Return the itinerary's destination profile for a region (fuzzy match)."""
    if not region or not config.ITINERARY_FILE.exists():
        return ""
    text = config.ITINERARY_FILE.read_text(encoding="utf-8")
    key = re.split(r"[(&]", region)[0].strip().split()[0].lower()
    for section in re.split(r"(?m)^## ", text):
        if key in section.splitlines()[0].lower():
            return "## " + section[:6000]
    return ""
