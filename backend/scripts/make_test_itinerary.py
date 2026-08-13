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
        "focus": "Museums, architecture and neighborhood food",
        "tz": "America/Chicago",
        "regions": [
            {
                "name": "The Loop & Millennium Park",
                "theme": "The Civic Core",
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
                "theme": "Michigan Avenue & the River",
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
                "theme": "University, Fair Grounds and Wright",
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
                "theme": "Mexican Chicago",
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
                "theme": "Boulevards & the Elevated Trail",
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
    # Northwest side and the near north suburbs — Skokie, Niles, Jefferson
    # Park. Eleven small areas rather than five big ones, so a three-week run
    # changes scenery every couple of days instead of repeating one stop list
    # for most of a week.
    #
    # Each region's FIRST WORD is unique on purpose. Destination profiles are
    # matched by splitting the region name on "(" or "&" and taking word one,
    # so "Skokie Village" and "Skokie Lagoons" would both resolve to the same
    # section and silently share stops.
    "chicago-north": {
        "title": "Chicago North Side & Near Suburbs — Test Trip",
        "blurb": "A three-week local stand-in for the Greece itinerary, "
                 "centered on Skokie, Niles and Jefferson Park.",
        "focus": "Immigrant neighborhoods, forest preserves and roadside landmarks",
        "tz": "America/Chicago",
        "regions": [
            {
                "name": "Skokie Village Center",
                "theme": "The Civic Core",
                "sites": [
                    ("Illinois Holocaust Museum & Education Center", "The major institution in the area; allow three hours and start with the permanent exhibition."),
                    ("Skokie Theatre", "Restored 1912 storefront theatre, now a small music and comedy room."),
                    ("Devonshire Cultural Center", "Village arts center with rotating local shows."),
                    ("Skokie Public Library", "Consistently rated among the best in the country; good place to sit out afternoon heat."),
                    ("Skokie Farmers Market", "Sunday mornings on Floral Avenue through October."),
                ],
                "dining": {
                    "Breakfast": ["Blueberry Hill Breakfast Cafe (Big menu, faster than the line suggests)"],
                    "Lunch": ["Pita Inn (The area's benchmark for shawarma, cash-efficient and fast)", "Kaufman's Bagel & Delicatessen (Old-school deli, get the whitefish salad)", "Ruby of Siam (Long-running Thai)"],
                    "Dinner": ["Libertad (Latin small plates, the ambitious room in town)", "Real Urban Barbecue (Brisket and burnt ends)", "Shallots Bistro (Kosher fine dining)"],
                },
            },
            {
                "name": "Oakton Street Corridor",
                "theme": "Green Space & Everyday Skokie",
                "sites": [
                    ("Emily Oaks Nature Center", "Thirteen acres of oak woodland with a short boardwalk loop."),
                    ("Skokie Northshore Sculpture Park", "Sixty-plus works along two miles of the North Shore Channel."),
                    ("Oakton Park", "Neighborhood park with the village pool and ball fields."),
                    ("Oakton College Skokie Campus", "Small gallery and a quiet campus to walk."),
                    ("North Shore Channel Trail", "Paved path running the length of the channel toward Evanston."),
                ],
                "dining": {
                    "Breakfast": ["Ken's Diner & Grill (Kosher diner, enormous portions)"],
                    "Lunch": ["Taboun Grill (Israeli grill)", "Slice of Life (Long-running kosher standby)", "Pita Inn (Worth repeating)"],
                    "Dinner": ["Kabul House (Afghan; the pumpkin borani is the thing to order)", "Ruby of Siam (Reliable Thai)", "Real Urban Barbecue (When nothing else will do)"],
                },
            },
            {
                "name": "Old Orchard & North Skokie",
                "theme": "Retail, Recreation and the Forest Edge",
                "sites": [
                    ("Westfield Old Orchard", "Open-air mall, unexpectedly pleasant to walk in late summer."),
                    ("Skokie Heritage Museum", "Village history in a 1887 firehouse, plus a log cabin out back."),
                    ("Weber Leisure Center", "Village recreation complex with an indoor track."),
                    ("Lorel Park", "Small quiet park, good for a morning coffee outdoors."),
                    ("Harms Woods", "Forest preserve along the North Branch; bridle trails and old oaks."),
                ],
                "dining": {
                    "Breakfast": ["Walker Bros. Original Pancake House (The apple pancake, non-negotiable)"],
                    "Lunch": ["Shake Shack Old Orchard (Reliable patio lunch)", "Hackney's on Harms (Famous for the onion loaf)", "Corner Bakery Cafe (Fast, fine)"],
                    "Dinner": ["Wildfire Glenview (Wood-fired steaks and chops)", "Hackney's on Harms (Again, unashamedly)", "Kabul House (Short drive back into Skokie)"],
                },
            },
            {
                "name": "Niles & the Leaning Tower",
                "theme": "Postwar Suburbia & Its Landmarks",
                "sites": [
                    ("Leaning Tower of Niles", "A half-scale replica of Pisa's tower, built in 1934 to hide a pool's water tanks."),
                    ("Niles Historical Museum", "Local history in a converted 1930s building."),
                    ("Grennan Heights Park", "Neighborhood park with a summer concert series."),
                    ("Niles Family Fitness Center", "Village facility with a good lap pool."),
                    ("St. Adalbert Cemetery", "Vast Polish-Catholic cemetery with notable funerary sculpture."),
                ],
                "dining": {
                    "Breakfast": ["Kappy's American Grill & Pancake House (Pancake-house institution)"],
                    "Lunch": ["Superdawg Drive-In (Carhop service since 1948; get the Whoopskidawg)", "Pita Inn Niles (Same operation, shorter line)", "Rosati's Pizza (Thin crust, tavern cut)"],
                    "Dinner": ["Cafe Touche (Edison Park French, quietly excellent)", "Lou Malnati's Lincolnwood (Deep dish, order on arrival)", "Rosati's Pizza (If the day ran long)"],
                },
            },
            {
                "name": "Golf Mill & Northwest Niles",
                "theme": "Mid-Century Commerce",
                "sites": [
                    ("Golf Mill Shopping Center", "1960s mall mid-redevelopment; a good look at suburban retail history."),
                    ("Tam O'Shanter Golf Course", "Village-run nine-hole course on the old Tam O'Shanter grounds."),
                    ("Ballard Park", "Small park with a walking loop."),
                    ("Notre Dame College Prep", "Landmark campus on Dempster."),
                    ("Jozwiak Park", "Quiet green space on the Des Plaines side."),
                ],
                "dining": {
                    "Breakfast": ["Golden Nugget Pancake House (Open early, open late)"],
                    "Lunch": ["Mitsuwa Marketplace Food Court (Japanese grocery with a ramen counter worth the drive)", "Panino's Pizzeria (Neighborhood Italian)", "Superdawg Drive-In (Still the best lunch in the area)"],
                    "Dinner": ["Fountain Blue Restaurant (Old-school Des Plaines supper club)", "Sabatino's (Live piano, Italian-American, unchanged since 1974)", "Cafe Touche (Worth the second visit)"],
                },
            },
            {
                "name": "Jefferson Park",
                "theme": "Polish Chicago",
                "sites": [
                    ("Copernicus Center", "The 1930 Gateway Theatre, now the heart of Polish Chicago's cultural life."),
                    ("Jefferson Memorial Park", "Neighborhood park with a fieldhouse and summer programming."),
                    ("Jefferson Park Transit Center", "Blue Line, Metra and a dozen bus routes converging — a good study in how the northwest side moves."),
                    ("Jefferson Park Sunday Market", "Seasonal market beside the transit center."),
                    ("Milwaukee Avenue Commercial Strip", "Polish delis, bakeries and taverns running north from Lawrence."),
                ],
                "dining": {
                    "Breakfast": ["Charlie's Restaurant (Diner breakfast, no ceremony)"],
                    "Lunch": ["Smak-Tak (Polish; the potato pancakes and pierogi)", "Gale Street Inn (Barbecue ribs since 1963)", "Fischman Liquors & Tavern (Beer selection far better than the storefront suggests)"],
                    "Dinner": ["Gale Street Inn (The ribs, properly, at dinner)", "Tre Kronor (Swedish on Foster, warm room)", "Smak-Tak (If lunch went well)"],
                },
            },
            {
                "name": "Norwood Park & Edgebrook",
                "theme": "The Oldest House & the Forest Preserves",
                "sites": [
                    ("Noble-Seymour-Crippen House", "The oldest building in Chicago, 1833; home of the Norwood Park Historical Society."),
                    ("Caldwell Woods", "Forest preserve with the Bunker Hill trailhead."),
                    ("LaBagh Woods", "Serious birding along the North Branch."),
                    ("Edgebrook Golf Course", "Cook County course laid out in 1919."),
                    ("Edgebrook Shopping District", "A few blocks of small storefronts around the Metra stop."),
                ],
                "dining": {
                    "Breakfast": ["Cozy Corner Restaurant & Pancake House (Northwest side breakfast, unpretentious)"],
                    "Lunch": ["Superdawg Drive-In (The neighborhood landmark)", "Zia's Trattoria (Edison Park Italian)", "Moretti's (Pizza and a patio)"],
                    "Dinner": ["Cafe Touche (French, small, book ahead)", "Zia's Trattoria (Reliable second choice)", "Gale Street Inn (Short hop back to Jefferson Park)"],
                },
            },
            {
                "name": "Devon Avenue & West Ridge",
                "theme": "The Immigrant Mile",
                "sites": [
                    ("Devon Avenue", "Two miles running from South Asian to Orthodox Jewish to Georgian within a few blocks — the best walk in the area."),
                    ("Rosehill Cemetery", "Chicago's largest, with a Gothic entrance by W.W. Boyington."),
                    ("Warren Park", "Big park with a golf course and a summer festival calendar."),
                    ("Indian Boundary Park", "Historic park with a lagoon and a 1929 Tudor fieldhouse."),
                    ("Croatian Cultural Center", "One of several diaspora institutions on the strip."),
                ],
                "dining": {
                    "Breakfast": ["Nhu Lan Bakery (Banh mi and Vietnamese coffee)"],
                    "Lunch": ["Ghareeb Nawaz (Cheap, fast, legendary)", "Uru-Swati (Vegetarian Indian, thali)", "Sabri Nihari (Pakistani; the nihari is the point)"],
                    "Dinner": ["Hema's Kitchen (Long-running North Indian)", "Khan BBQ (Kebabs and karahi)", "Udupi Palace (South Indian, dosas)"],
                },
            },
            {
                "name": "Lincolnwood & Peterson Avenue",
                "theme": "River, Trail and Roadside Signs",
                "sites": [
                    ("Proesel Park", "Lincolnwood's main park, with the aquatic center."),
                    ("Lincolnwood Town Center", "Small indoor mall; a period piece."),
                    ("Bunker Hill Forest Preserve", "Trails and a model-airplane field."),
                    ("Legion Park", "River-side park with a path along the North Branch."),
                    ("North Shore Channel Trail North", "The Lincolnwood stretch of the channel path."),
                ],
                "dining": {
                    "Breakfast": ["Baker's Square (Pie for breakfast is a legitimate choice)"],
                    "Lunch": ["Lou Malnati's Lincolnwood (Deep dish takes 45 minutes; plan)", "Wolfy's Hot Dogs (The giant sign on Peterson)", "Kaufman's Bagel & Delicatessen (Back toward Skokie)"],
                    "Dinner": ["Chicago Kalbi (Korean barbecue on Lincoln)", "Cho Sun Ok (Small, excellent, cash preferred)", "Lou Malnati's Lincolnwood (No shame in twice)"],
                },
            },
            {
                "name": "Evanston Lakefront",
                "theme": "The Lake and the University",
                "sites": [
                    ("Grosse Point Lighthouse", "1873 lighthouse; tower tours on summer weekends."),
                    ("Northwestern University Lakefill", "Landfill peninsula with the best skyline view north of the city."),
                    ("Evanston History Center (Dawes House)", "Home of the Nobel-winning vice president, on the lakefront."),
                    ("Ladd Arboretum", "Seventeen acres along the canal with a bird sanctuary."),
                    ("Lighthouse Beach", "Swimming beach beneath the lighthouse."),
                ],
                "dining": {
                    "Breakfast": ["Lucky Platter (Eccentric room, very good breakfast)"],
                    "Lunch": ["Hecky's Barbecue (It's the sauce)", "Mustard's Last Stand (Hot dogs by the Northwestern stadium)", "Buffalo Joe's (Wings, a student institution)"],
                    "Dinner": ["Found Kitchen and Social House (Seasonal small plates)", "Oceanique (French seafood, the special-occasion room)", "Campagnola (Italian, quiet)"],
                },
            },
            {
                "name": "Portage Park & Old Irving",
                "theme": "Movie Palaces & the Six Corners",
                "sites": [
                    ("Portage Park", "The 1959 Pan American Games pool where Olympic trials were swum."),
                    ("Portage Theater", "1920 movie palace on Milwaukee Avenue."),
                    ("Six Corners", "The Irving Park, Cicero and Milwaukee junction — the old northwest side downtown."),
                    ("Independence Park", "Shaded park at the heart of Old Irving."),
                    ("Irving Park Road Commercial Strip", "Diners, taverns and a good bakery or two."),
                ],
                "dining": {
                    "Breakfast": ["Cozy Corner Restaurant & Pancake House (Second visit, no apologies)"],
                    "Lunch": ["Smoque BBQ (Among the best barbecue in the city; go before noon)", "Chuck's Pizza (Tavern-cut, neighborhood standard)", "Superdawg Drive-In (One last time)"],
                    "Dinner": ["Sabatino's (Piano bar, Italian-American, a time capsule)", "Smoque BBQ (If the line beat you at lunch)", "Tre Kronor (Ending on the Swedish note)"],
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
    """Emit the same document shape as the real Greece itinerary.

    Frontmatter, "# Itinerary Overview" with the region table, then
    "# Destination Profiles" with a numbered "## N. Name (Days X-Y)" heading,
    a Theme line, Key Sites bullets and a Dining table per region. Matching
    the real file matters beyond tidiness: it is what the concierge retrieves
    and what the parser walks, so a test itinerary shaped differently would
    exercise a different code path than the trip will.
    """
    spec = CITIES[city]
    regions = spec["regions"]
    blocks = month_blocks(start, days, len(regions))
    used = sorted({i for i, _, _ in blocks})
    end = start + dt.timedelta(days=days - 1)

    def trip_day(d: dt.date) -> int:
        return (d - start).days + 1

    out = [
        "---",
        "type: itinerary",
        f"title: {spec['title']}",
        f"duration: {days} days ({days - 1} nights)",
        f"dates: {start.strftime('%B %-d')} - {end.strftime('%B %-d, %Y')}",
        f"focus: {spec['focus']}",
        "source_document: generated by scripts/make_test_itinerary.py (local testing)",
        "---",
        "",
        "# Itinerary Overview",
        "",
        "| Region / Stop | Days Allocated | Dates |",
        "|---|---|---|",
    ]
    for i, a, b in blocks:
        n = (b - a).days + 1
        out.append(f"| {regions[i]['name']} | {n} Day{'s' if n > 1 else ''} | {fmt_range(a, b)} |")
    out += ["", "---", "", "# Destination Profiles", ""]

    for n, i in enumerate(used, 1):
        r = regions[i]
        mine = [(a, b) for j, a, b in blocks if j == i]
        lo, hi = trip_day(mine[0][0]), trip_day(mine[-1][1])
        day_label = f"Day {lo}" if lo == hi else f"Days {lo}-{hi}"
        # The heading must contain the region's first word: destination
        # profiles are matched by splitting the region name on "(" or "&"
        # and taking word one.
        out += [f"## {n}. {r['name']} ({day_label})",
                f"**Theme:** {r.get('theme', 'Local testing')}",
                "", "### Key Sites & Activities", ""]
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
