# Niko iOS App — Build Specification

Complete, self-contained spec for building the Niko iOS client. Written for an
agent/developer picking this up cold. The interactive HTML prototype that these
screens were designed against is the visual reference; this document is the
contract.

---

## 1. Product context

Niko is a personal AI travel concierge for **one user** on a 21-day spiritual &
historical tour of Greece (**Sept 5–25**). Two core jobs:

1. **On-demand concierge** — answer questions about sites, food, transit, and
   hours in the moment, grounded in the user's itinerary and journal (RAG on
   the backend).
2. **Conversational journaling** — capture feedback about places just visited,
   resolve them to real Google Places entries, and feed the results into
   future recommendations.

The app is a **thin client**. All intelligence lives on the backend
(FastAPI on Render); the app's responsibilities are: text input, GPS context,
rendering, offline caching, and deep-linking to Google Maps. There is no LLM
call, no API key for Google/Anthropic, and no place-resolution logic on the
device.

**Hard deadline: the app must be on the user's phone (TestFlight) by Sept 1.**
Working and boring beats clever and late. No third-party dependencies.

## 2. Platform & conventions

| Item | Decision |
|---|---|
| UI framework | SwiftUI, iOS 17+ |
| Visual direction | Utilitarian, native components, system fonts. No custom design system. |
| Dependencies | None. URLSession, MapKit, CoreLocation, Foundation only. |
| Voice input | The iOS keyboard's built-in dictation mic. **Do not** add SFSpeechRecognizer or any custom mic UI. |
| Maps | Apple **MapKit** for the in-app map. Google Maps is reached only via outbound `Link`s to `maps_url` values the backend supplies. |
| Location | CoreLocation, `whenInUse`, hundred-meter accuracy. Coordinates ride along on chat/journal requests; a reverse-geocoded name feeds the location chip. |
| Accent semantics | System blue = concierge/recommendations. Orange = Journal mode (nav tint, send button, pins). Green/red = like/dislike + best/worst. These are mode signals, keep them consistent. |
| Errors | Inline, never blocking alerts (exception: the "Saved" confirmation). The user is mid-walk in a foreign country — a modal is hostile. |

## 3. Existing code (already in the repo)

`ios/Niko/` contains a working first pass of every file below. Treat it as the
starting point — extend it, don't rewrite it wholesale. Known gaps are marked
**TODO** throughout this spec.

```
NikoApp.swift                 entry point, injects LocationManager
ContentView.swift             TabView, owns cross-tab state (recommendedPlaces, selectedTab)
Models/Models.swift           Codable models matching the API contract (§6)
Services/APIClient.swift      async/await client; base URL + token from Info.plist
Services/LocationManager.swift CoreLocation wrapper + reverse geocoding
Services/CacheStore.swift     JSON file cache (offline reads); queue is TODO
Views/AskView.swift           chat UI, memory toggle, starter prompts, map handoff
Views/JournalView.swift       journal chat, candidate card, Done flow
Views/MapView.swift           MapKit, two pin layers, detail card
Views/TodayView.swift         Morning Guide + Evening Recap, offline banner
Views/JourneyView.swift       segmented Places/Insights, preferences, detail
```

Xcode project setup steps (create project, reference sources, Info.plist keys,
signing, TestFlight) are in `ios/README.md`. Required Info.plist keys:
`NSLocationWhenInUseUsageDescription`, `NikoBaseURL`, `NikoAPIToken`.

## 4. Information architecture

Five tabs. Ask is the default. Tab identity matters — each has a distinct job
and the user should never be confused about which mode they're in.

```
┌──────┬─────────┬──────┬───────┬─────────┐
│ Ask  │ Journal │ Map  │ Today │ Journey │
└──────┴─────────┴──────┴───────┴─────────┘
```

---

## 5. Screen-by-screen specification

### 5.1 Ask (concierge) — default tab

**Job:** in-the-moment answers, grounded in location + itinerary + journal.

Layout, top to bottom:

1. **Nav bar** — title "Ask Niko"; trailing **location chip** showing the
   reverse-geocoded neighborhood/city (e.g. "Plaka, Athens"). Hidden when
   location is unavailable. Purpose: signals Niko knows where you are.
2. **Thread** — chat bubbles. User right/blue/white-text; Niko left/gray.
   Auto-scroll to newest. While waiting: a progress indicator in the thread
   (typing-dots feel), not a full-screen spinner.
3. **Empty state** (no messages yet): 🏛️ glyph, "Ask me anything out here",
   one-line subtitle, and 3 tappable starter prompts that send immediately.
   Starters should be trip-relevant (site history, "Where should I eat
   nearby?", hours).
4. **Trip memory bar** — a 📓 toggle pill above the input. OFF (default):
   normal concierge. ON: pill fills blue, helper text switches to "Answers
   come from your trip archive", input placeholder becomes "Ask about your
   trip so far…". The toggle simply flips `memory_mode` in the request.
5. **Input bar** — multiline `TextField` + send button. Dictation comes free
   from the keyboard mic.

**Behaviors:**

- **Ask→Map handoff (key interaction):** when a response's `places[]` is
  non-empty, render a prominent "Show these on the map" button under the
  bubble. Tapping it stores the places in shared state and switches to the
  Map tab, where they appear as blue pins. New recommendations replace the
  previous set (recommendation pins are ephemeral; journal pins are
  permanent).
- **Source citations:** in memory mode, non-empty `sources[]` renders as a
  small blue "📓 …" caption under the bubble. This is the trust feature —
  when the AI claims to remember, it shows where the memory came from.
- **Errors:** append an inline Niko-styled bubble with the error text
  (offline copy: "No connection — Niko needs data to answer."). The user's
  message stays visible so they can re-send.
- **TODO:** persist the thread across launches (currently in-memory only) —
  a simple Codable dump of the last N messages via CacheStore is enough.

### 5.2 Journal (feedback capture)

**Job:** conversational review of a place just visited, resolved to a real
Google Place. Visually distinct: **orange** tint throughout.

Layout: optional **Maps-link paste field** (visible only before the entry
starts) → thread → input bar. Nav bar has a trailing **Done** button
(disabled until an entry exists) and, once a place is confirmed, a pinned
orange strip with the place name.

**Flow (state machine):**

1. Fresh tab shows Niko's opener ("How was it? Tell me about somewhere you
   just went…") locally — no network yet.
2. First user send → `POST /api/journal/start` (with the pasted link, if any),
   then `POST /api/journal/message`.
3. If the response carries a `candidate`, render the **candidate card** inline:
   place name, address, "Is this the place?", **Yes, that's it** (orange,
   prominent) / **No** buttons. Input is disabled while a card is pending.
   - Yes → `POST /api/journal/confirm {accepted: true}` → pin the place name
     above the thread; conversation continues.
   - No → `confirm {accepted: false}` → Niko acknowledges, entry proceeds
     unlinked ("Unconfirmed location" placeholder downstream).
4. Subsequent sends are plain `journal/message` calls; the backend runs the
   interview (one question per reply).
5. **Done** → `POST /api/journal/finish` → backend extracts sentiment/summary
   and files the entry. Reset the tab to fresh state and confirm with a
   "Saved to your Journey ✓" alert.

**Behaviors:**

- The user decides when the entry is over (explicit Done), never the AI.
- Leaving the tab mid-conversation must not lose the draft: state lives in
  the view model and survives tab switches. **TODO:** persist the draft
  (entry_id + transcript) via CacheStore so force-quit doesn't lose it.
- **TODO (offline queue):** composing offline should queue the entry locally
  and sync on reconnect — see §7.

### 5.3 Map

**Job:** spatial view of the trip — where you've been (journal) and where
Niko suggests going (recommendations).

- MapKit map, starts at user location (fallback: Athens).
- **Two toggleable layers**, chips pinned at the top:
  - **My places** (orange pins) — from `GET /api/map/pins`; permanent record.
  - **Recommendations** (blue pins) — the ephemeral set handed off from Ask.
- `UserAnnotation()` shows the blue current-location dot.
- Tapping a pin opens a **bottom detail card** (material background):
  - Journal pin: place name, one-line verdict, "Open in Google Maps ↗" link.
  - Recommendation pin: name, address + rating, Maps link.
  - One card at a time; ✕ to dismiss.
- Pull-to-refresh refetches pins; pins cache for offline display.
- **TODO:** when the trip spans regions, auto-fit the camera to the visible
  pin set instead of a fixed region.

### 5.4 Today

**Job:** the day's briefing, generated server-side (7 AM guide, 8 PM recap).

- Nav title: "Day N · Region" from the `/api/today` response ("Today" before
  the trip starts).
- **Morning Guide section** — one card per stop: name, hours pill (green;
  style warnings differently if the text implies caution), 2-sentence blurb,
  and a 💡 tip in a tinted inset. A lunch line follows the stops.
  Empty state: "Your morning guide lands at 7 AM."
- **Evening Recap section** — narrative paragraph, then one row per journal
  entry (place, one-liner, Maps link). Empty state: "Tonight's recap lands at
  8 PM — journal something today and it'll show up here."
- Pull-to-refresh. On network failure, serve the cached payload and show an
  unobtrusive "Offline — showing your last synced guide" banner.

### 5.5 Journey

**Job:** the trip's memory made visible. Segmented control: **Places** |
**Insights**.

**Places segment:**

- "What Niko's learned" — horizontally scrolling preference chips
  (green "Likes: …", red "Dislikes: …") from `preferences`. Hide when empty.
- Entry list: place name (or "Unconfirmed location"), sentiment emoji
  (loved 😍 / mixed 🙂 / skip 😕), one-line verdict. Newest first.
- Tap → **detail screen**: Niko's summary, Best/Worst rows (green/red), and
  either the Google Maps link or an explicit "Unconfirmed location — no link"
  row. Never hide the unlinked state; it's honest.

**Insights segment:**

- Cards: emoji + 1–2 sentence fact + uppercase tag (e.g. "SEPT 6 · DIGEST").
- Footer copy explains the generation rule: "Generated once or twice a day
  whenever you've logged 2+ moments in the last 24 hours."
- Empty state explains insights arrive after a day of activity.

---

## 6. API contract

Base URL and static bearer token come from Info.plist (`NikoBaseURL`,
`NikoAPIToken`). Every request: `Authorization: Bearer <token>`. All bodies
JSON, snake_case keys (the Codable models in `Models.swift` already map them).
Timeout 60s — concierge answers with tool calls can take 10–30s; show
progress, don't time out early.

| Endpoint | Request → Response |
|---|---|
| `POST /api/chat` | `{message, lat?, lon?, memory_mode}` → `{reply, places[], sources[]}` |
| `POST /api/journal/start` | `{maps_link?}` → `{entry_id, reply}` |
| `POST /api/journal/message` | `{entry_id, message, lat?, lon?}` → `{reply, candidate?}` |
| `POST /api/journal/confirm` | `{entry_id, accepted}` → `{reply}` |
| `POST /api/journal/finish` | `{entry_id}` → `{entry}` |
| `GET /api/today` | → `{trip_day?, date, region?, morning_guide?, evening_recap?}` |
| `GET /api/places` | → `{entries[], preferences{likes[], dislikes[]}}` |
| `GET /api/insights` | → `{insights[]}` |
| `GET /api/map/pins` | → `{pins[]}` |

Key shapes (full definitions in `Models.swift`):

- **Place** (recommendations + candidates): `place_id?, name?, address?, lat?,
  lon?, category?, rating?, rating_count?, maps_url?`
- **JournalEntry:** `id, created_at, place_name?, maps_url?, lat?, lon?,
  sentiment? (loved|mixed|skip), line?, summary?, best?, worst?`
- **MorningGuide:** `stops[{name, hours, blurb, tip}], lunch`
- **EveningRecap:** `narrative, entries[{place_name?, sentiment?, line?, maps_url?}]`
- **Insight:** `id, emoji?, text, tag?`
- **MapPin:** `id, place_name?, lat, lon, sentiment?, line?, maps_url?`

Treat every optional as genuinely optional — the backend degrades (e.g. no
Places key → no candidates, `maps_url` null) and the UI must not crash or
render "nil".

## 7. Offline strategy (required — Mt Athos, Sept 20–23)

The trip includes ~4 days of near-zero connectivity plus ferry dead zones.
Rules:

1. **Reads:** every successful `GET` payload (today, places, pins) is cached
   to disk (`CacheStore`). On network failure, render the cache with a quiet
   offline banner. Never show an empty screen if a cache exists.
2. **Ask:** requires the network. Offline, show the honest inline error — no
   fake answers, no queuing of questions.
3. **Journal (TODO, week-3 priority):** compose fully offline. Queue the
   transcript locally; on reconnect, replay it through start/message/finish
   (skip place confirmation for queued entries — file them unlinked, the
   backend accepts entries without a place). Surface queued state in the UI
   ("1 entry waiting to sync").
4. Morning guides for the Athos days are pre-generated server-side; the
   client just needs its `today` cache warm (opening the tab any time on
   Sept 19 with signal is sufficient — no extra client work).

## 8. Non-functional requirements

- **No secrets in the repo.** The API token lives in Info.plist locally /
  build settings; it is not committed.
- **Battery:** significant-location-changes monitoring only; no continuous
  GPS.
- **Accessibility:** Dynamic Type must not break layouts (test at XL);
  buttons get labels; color is never the only signal (sentiment also has
  emoji, layers also have text chips).
- **Resilience:** any decode failure or 5xx surfaces as an inline retryable
  message; the app never crashes on unexpected nulls.
- **Distribution:** TestFlight by Sept 1 (dev-profile installs expire; see
  `ios/README.md`).

## 9. Explicitly out of scope for V1

- TTS voice output, custom speech recognition, push-to-talk UI
- Push notifications (digest stays passive in the Insights tab)
- Multi-user, auth flows, accounts
- In-app itinerary editing (the itinerary is Markdown in the repo)
- Google Maps SDK / in-app Google tiles
- iPad layouts, widgets, watch app

## 10. Acceptance checklist

- [ ] Ask: starter prompt → grounded answer; "Where should I eat nearby?" →
      answer with places → "Show these on the map" lands on blue pins
- [ ] Trip memory ON → question about a past entry → answer with 📓 source
- [ ] Journal: full happy path (resolve → Yes → interview → Done → appears in
      Journey, Map, and that evening's recap)
- [ ] Journal: "No" path files an Unconfirmed entry with placeholder in detail
- [ ] Today: renders both sections; airplane mode shows cached copy + banner
- [ ] Journey: preferences chips reflect logged likes/dislikes; entry detail
      matches the finished journal entry
- [ ] Map: both layers toggle; pin cards deep-link to Google Maps
- [ ] Kill the app mid-journal-draft → draft survives relaunch
- [ ] Full flow works on a physical device over cellular
