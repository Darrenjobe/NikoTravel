#!/usr/bin/env python3
"""Generate a throwaway itinerary that covers *today*, for local testing.

The real itinerary is Sept 5–25 in Greece, so until then every date-driven
feature — the Morning Guide, today's stops, ambient context, trip day — sits
idle and answers "no itinerary region for today". This writes a parseable
itinerary around the current date so the whole experience can be exercised
from a desk in Chicago.

    python3 scripts/make_test_itinerary.py                 # 5 days from today
    python3 scripts/make_test_itinerary.py --days 3
    python3 scripts/make_test_itinerary.py --start 2026-08-20

It writes to testdata/<city>/ by default, which is a *separate* knowledge
directory. That matters: dropping a test itinerary into knowledge/ would put
Chicago restaurants into the same Chroma collection the concierge retrieves
from for Greece.

Two things about the format are easy to get wrong and fail silently, so this
generator handles both and then parses its own output to prove it:

  * Month names need four letters. "Aug 13-17" does not parse — the lookup
    table is keyed on the first four characters, so it must be "August".
  * A date range takes its month from the start only, so "August 30 -
    September 2" parses as August 30 to August *2*. Blocks are therefore
    split at month boundaries.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent

# Real places, deliberately. Google Places has to resolve them when you
# journal, recommendations have to return something true, and the concierge
# should have real ground to stand on — a fake itinerary of invented cafes
# tests the plumbing but not the experience.
CITIES = {
    "chicago": {
        "title": "Chicago Test Trip",
        "blurb": "A local stand-in for the Greece itinerary, used to exercise "
                 "the daily guide, journaling and concierge from home.",
        "tz": "America/Chicago",
        "regions": [
            {
                "name": "The Loop & Millennium Park",
                "sites": [
                    ("Art Institute of Chicago", "One of the great encyclopedic museums; the Impressionist rooms and Thorne Miniature Rooms are the draws."),
                    ("Cloud Gate (The Bean)", "Anish Kapoor's mirrored sculpture in Millennium Park; best photographed early before crowds."),
                    ("Chicago Riverwalk", "A mile and a half of promenade along the river's south bank, lined with bars and architecture."),
                    ("Willis Tower Skydeck", "103rd-floor glass ledges over the city; go at dusk for both daylight and lights."),
                    ("Chicago Cultural Center", "Free, and home to the world's largest Tiffany stained-glass dome."),
                ],
                "dining": {
                    "Breakfast": ["Wildberry Pancakes and Cafe (Perennial line, worth it)"],
                    "Lunch": ["Cafecito (Cuban sandwiches near Grant Park)", "Revival Food Hall (Fifteen local vendors under one roof)", "Miller's Pub (Old-school Loop institution)"],
                    "Dinner": ["Italian Village (Three restaurants, open since 1927)", "Acanto (Italian across from Millennium Park)", "Cindy's (Rooftop dining over Grant Park)"],
                },
            },
            {
                "name": "Near North & River North",
                "sites": [
                    ("Museum of Contemporary Art", "Strong rotating exhibitions and a terrace overlooking Lake Shore Park."),
                    ("Navy Pier", "Touristy but the Centennial Wheel gives the best lake-side view of the skyline."),
                    ("Chicago Water Tower", "One of the few structures to survive the 1871 fire; small free gallery inside."),
                    ("Holy Name Cathedral", "Seat of the Archdiocese of Chicago; quiet mid-afternoon."),
                    ("Magnificent Mile", "The Michigan Avenue stretch north of the river, good for walking the architecture."),
                ],
                "dining": {
                    "Breakfast": ["Beatrix (Reliable breakfast and very good coffee)"],
                    "Lunch": ["Portillo's (Italian beef and Chicago dogs)", "Lou Malnati's (Deep dish, order it when you sit down)", "Xoco (Rick Bayless's Mexican street food)"],
                    "Dinner": ["Gene & Georgetti (Chicago steakhouse since 1941)", "RPM Italian (Loud, modern, good pasta)", "Coco Pazzo (Tuscan, quieter room)"],
                },
            },
            {
                "name": "Hyde Park & the South Side",
                "sites": [
                    ("Museum of Science and Industry", "A captured German U-boat, a coal mine, and the 1893 World's Fair's last building."),
                    ("Frederick C. Robie House", "Frank Lloyd Wright's Prairie School masterwork; timed tickets only."),
                    ("University of Chicago Main Quadrangles", "English Gothic quads worth a slow walk."),
                    ("Osaka Garden, Jackson Park", "A Japanese garden on the Wooded Island, left from the 1893 Exposition."),
                    ("DuSable Black History Museum", "The country's oldest independent Black history museum."),
                ],
                "dining": {
                    "Breakfast": ["Valois Cafeteria (Cash-only cafeteria, a neighborhood institution)"],
                    "Lunch": ["Medici on 57th (Student haunt, carved-up wooden booths)", "Nella Pizza e Pasta (Neapolitan, family-run)", "Ja' Grill (Jamaican)"],
                    "Dinner": ["Virtue Restaurant (Southern cooking, one of the city's best)", "The Promontory (Hearth-cooked, live music upstairs)", "Chant (Pan-Asian near the quads)"],
                },
            },
            {
                "name": "Pilsen & Little Village",
                "sites": [
                    ("National Museum of Mexican Art", "Free, and the largest Mexican art collection in the country."),
                    ("16th Street Murals", "A continuous stretch of muralwork along the rail embankment."),
                    ("Thalia Hall", "1892 opera house modelled on Prague's; now a music venue."),
                    ("St. Adalbert Church", "Twin-towered Polish basilica from Pilsen's earlier immigrant era."),
                    ("Harrison Park", "The neighborhood's center of gravity on a weekend afternoon."),
                ],
                "dining": {
                    "Breakfast": ["Cafe Jumping Bean (Corner cafe, been there since 1994)"],
                    "Lunch": ["Carnitas Uruapan (Pork by the pound, cash only)", "Don Pedro Carnitas (The other side of that argument)", "5 Rabanitos (Refined Mexican from an Ex-Topolobampo chef)"],
                    "Dinner": ["Dusek's Board & Beer (Under Thalia Hall)", "S.K.Y. (Tasting-menu-adjacent, modern)", "Pl-zen (Mexican with a long bar)"],
                },
            },
            {
                "name": "Wicker Park & Logan Square",
                "sites": [
                    ("The 606 / Bloomingdale Trail", "An elevated rail line turned 2.7-mile park; walk it east to west."),
                    ("Illinois Centennial Monument", "The column at Logan Square's center, ringed by the boulevard."),
                    ("Flat Iron Arts Building", "Artist studios in a triangular 1913 building at the six corners."),
                    ("Myopic Books", "Three floors of used books, open late."),
                    ("Humboldt Park Boathouse", "Prairie-style boathouse on the lagoon, good at golden hour."),
                ],
                "dining": {
                    "Breakfast": ["Bang Bang Pie & Biscuits (Biscuits and a back patio)"],
                    "Lunch": ["Big Star (Tacos and whiskey, big patio)", "Antique Taco (Smaller, quieter, very good)", "Handlebar (Vegetarian-leaning, bike-shop energy)"],
                    "Dinner": ["Kasama (Filipino; the tasting menu has a Michelin star)", "Lula Cafe (Logan Square's anchor since 1999)", "Longman & Eagle (Whiskey list and a hotel upstairs)"],
                },
            },
        ],
    },
}


def month_blocks(start: dt.date, days: int, n_regions: int) -> list[tuple[int, dt.date, dt.date]]:
    """Split the trip into (region_index, start, end) runs that never cross a
    month boundary — a range takes its month from the start date only, so
    "August 30 - September 2" would parse as August 30 to August 2."""
    per = max(1, days // n_regions)
    blocks: list[tuple[int, dt.date, dt.date]] = []
    day = start
    for i in range(n_regions):
        remaining = (start + dt.timedelta(days=days - 1)) - day
        if remaining.days < 0:
            break
        length = per if i < n_regions - 1 else remaining.days + 1
        block_end = day + dt.timedelta(days=length - 1)
        cursor = day
        while cursor <= block_end:
            # last day of cursor's month
            nxt_month = cursor.replace(day=28) + dt.timedelta(days=4)
            month_end = nxt_month - dt.timedelta(days=nxt_month.day)
            piece_end = min(block_end, month_end)
            blocks.append((i, cursor, piece_end))
            cursor = piece_end + dt.timedelta(days=1)
        day = block_end + dt.timedelta(days=1)
    return blocks


def fmt_range(a: dt.date, b: dt.date) -> str:
    # Full month name: the parser keys on the first four characters, so "Aug"
    # silently fails to parse while "August" works.
    month = a.strftime("%B")
    return f"{month} {a.day}" if a == b else f"{month} {a.day}-{b.day}"


def build(city: str, start: dt.date, days: int) -> str:
    spec = CITIES[city]
    regions = spec["regions"]
    blocks = month_blocks(start, days, len(regions))
    used = sorted({i for i, _, _ in blocks})

    out = [f"# {spec['title']}", "", spec["blurb"], "",
           "> Generated by scripts/make_test_itinerary.py for local testing.",
           "> Not the real trip — see greece-spiritual-historical-tour.md.", "",
           "## Overview", "",
           "| Region / Stop | Days Allocated | Dates |", "|---|---|---|"]
    for i, a, b in blocks:
        n = (b - a).days + 1
        out.append(f"| {regions[i]['name']} | {n} Day{'s' if n > 1 else ''} | {fmt_range(a, b)} |")
    out.append("")

    for n, i in enumerate(used, 1):
        r = regions[i]
        mine = [(a, b) for j, a, b in blocks if j == i]
        span = fmt_range(mine[0][0], mine[-1][1])
        # The heading must contain the region's first word: sections are
        # matched by splitting the region name on "(" or "&" and taking it.
        out += [f"## {n}. {r['name']} ({span})", "", "### Key Sites & Activities", ""]
        out += [f"* **{name}:** {blurb}" for name, blurb in r["sites"]]
        out += ["", "### Dining Recommendations", "",
                "| Meal | Option 1 | Option 2 | Option 3 |", "|---|---|---|---|"]
        for meal in ("Breakfast", "Lunch", "Dinner"):
            opts = (r["dining"].get(meal, []) + ["-", "-", "-"])[:3]
            out.append(f"| **{meal}** | {opts[0]} | {opts[1]} | {opts[2]} |")
        out += ["", "---", ""]
    return "\n".join(out).rstrip() + "\n"


def verify(path: Path, city: str, start: dt.date, days: int) -> int:
    """Parse the file back with the real parser. A test itinerary that fails to
    parse looks identical to no itinerary at all, so never ship one unchecked."""
    import os
    os.environ["ITINERARY_FILE"] = str(path)
    os.environ.setdefault("API_TOKEN", "unused-for-parsing")
    sys.path.insert(0, str(BACKEND))
    from app import config
    config.ITINERARY_FILE = path
    config.TRIP_YEAR = start.year
    from app.services import itinerary, tripday
    tripday.clear_cache(); itinerary.clear_cache()

    sched = tripday.schedule()
    parsed = itinerary.days()
    today_ctx = tripday.context(start)

    print(f"\n  parsed {len(sched)} region rows, {len(parsed)} trip days")
    if not sched:
        print("  FAILED: no regions parsed", file=sys.stderr)
        return 1
    if len(parsed) != days:
        print(f"  WARNING: expected {days} days, got {len(parsed)}", file=sys.stderr)
    if not today_ctx["region"]:
        print(f"  FAILED: {start} maps to no region", file=sys.stderr)
        return 1

    print(f"  {start} -> day {today_ctx['trip_day']}, {today_ctx['region']}")
    first = parsed[0]
    print(f"  stops on day 1: {len(first['stops'])}  "
          f"({', '.join(s['name'] for s in first['stops'][:2])}…)")
    print(f"  dining on day 1: {', '.join(d['meal'] for d in first['dining'])}")
    if not first["stops"] or not first["dining"]:
        print("  FAILED: a day parsed with no stops or no dining", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--city", default="chicago", choices=sorted(CITIES))
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--start", default="today", help="YYYY-MM-DD or 'today'")
    ap.add_argument("--out", default=None, help="Defaults to testdata/<city>/itinerary/<city>.md")
    args = ap.parse_args()

    start = (dt.date.today() if args.start == "today"
             else dt.date.fromisoformat(args.start))
    out = Path(args.out) if args.out else (
        REPO / "testdata" / args.city / "itinerary" / f"{args.city}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(args.city, start, args.days), encoding="utf-8")

    print(f"Wrote {out}")
    rc = verify(out, args.city, start, args.days)
    if rc:
        return rc

    spec = CITIES[args.city]
    knowledge = out.parent.parent
    print(f"""
Run the backend against it — note KNOWLEDGE_DIR points at a separate tree, so
Chicago never enters the Chroma collection the concierge uses for Greece:

  cd backend
  KNOWLEDGE_DIR={knowledge} \\
  ITINERARY_FILE={out} \\
  DATA_DIR={BACKEND}/testdata-data \\
  TRIP_TZ={spec['tz']} TRIP_YEAR={start.year} \\
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Then, in another tab:

  scripts/job.sh reindex     # must report trip_days_parsed: {args.days}
  scripts/job.sh morning
  curl -H "Authorization: Bearer $API_TOKEN" localhost:8000/api/today
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
