# Hodegos iOS App — Current Frontend State

Generated: 2026-08-12

**Stack:** SwiftUI, iOS 17+, MapKit, CoreLocation. No third-party packages. Communicates with a REST backend via `APIClient` over HTTP/HTTPS.

---

## Architecture

```
HodegosApp
  └─ ContentView (TabView, 6 tabs)
       ├─ HomeView          [tab 0]
       ├─ AskView           [tab 1]
       ├─ JournalView       [tab 2]
       ├─ TripMapView       [tab 3]
       ├─ TodayView         [tab 4]
       └─ JourneyView       [tab 5]
```

`LocationManager` is injected as an `@EnvironmentObject` into every view that needs coordinates. Backend configuration (base URL, API token) lives in `Info.plist` and is read at launch by `APIClient`.

---

## Design System (`Theme.swift`, `Components.swift`)

**Palette** — limestone paper background (`#F6F2E9`), Aegean blue for Ask/concierge actions, Terracotta for Journal, Olive for positive/liked, Crimson for negative/warnings.

**Typography** — system serif (`hodDisplay`) for place names and headings, system monospaced (`hodMeta`) for section labels and metadata.

**Shared components:**

| Component | Used in |
|---|---|
| `MessageBubble` | Ask, Journal — renders AI and user messages with full markdown support (bold, italic, headers, lists) |
| `CandidateCard` | Journal — confirms the place being logged |
| `PinDot` | Map — 18pt coloured circle annotation |
| `FlowChips` | Journey — horizontal scrolling tag pills |
| `HodLabel` | All — uppercase monospaced section headers |
| `HoursPill` | Today, Home — hours badge; turns crimson when closing soon |
| `.hodScreen()` | All — applies paper background + tint per view |

---

## Views

### Home (`HomeView`)
- App name (`Ὁδηγός`) and tagline as hero header
- Loads `TodayResponse` from cache immediately, then refreshes from `/api/today`
- Shows today's morning guide stops as cards (name, blurb, `HoursPill`)
- Shows evening digest narrative if available
- Static "Quick Tips" section explaining how to use the app
- Navigation title shows "Day N" when trip day is known
- **Hamburger menu** (top-right) opens `SidebarMenuView` sheet: connection settings info, how-it-works notes, about section

### Ask (`AskView`)
- Full-screen chat interface with Nikos (the AI concierge)
- **Empty state:** three starter question buttons, serif headline prompt
- **Thread:** scrollable message list; AI replies render full markdown; each reply can include a "Show these on the map" button that pushes recommended places to the Map tab and switches to it
- **Memory mode toggle:** switches between general questions and questions answered from the user's trip archive (sent to backend as `memory_mode: true`)
- Every request sends: `message`, `lat`, `lon`, `memory_mode`, `timestamp` (ISO 8601)
- **New conversation button** (top-left, visible when thread exists): clears messages and input instantly
- **Keyboard:** `scrollDismissesKeyboard(.interactively)` + "Done" button on keyboard toolbar

### Journal (`JournalView`)
- Conversational journaling: user describes a place they just visited; Nikos asks follow-up questions and extracts structured data
- Optional Google Maps link field shown before first message (pre-populates location context)
- **Confirmed place banner** (terracotta) shown when the backend has matched a place
- `CandidateCard` shown when backend suggests a place match: Yes/No confirmation
- **Done button** (top-right): calls `POST /api/journal/finish` to save the entry and reset
- **New entry button** (top-left, visible when in-progress): alert with *Save & Start New* / *Discard* / *Cancel*
- **Keyboard:** same fix as Ask (`scrollDismissesKeyboard` + Done)
- Backend calls: `journalStart` → `journalMessage` (loop) → `journalConfirm` (optional) → `journalFinish`

### Map (`TripMapView`)
- Full-screen `Map` view with `UserAnnotation`
- **Three pin types:** Terracotta = journaled places, Aegean = AI recommendations (from Ask), Olive = local search results
- **Legend bar (top overlay):** toggles for "My places" and "Recommendations", plus **Find My Location** button that re-centres the camera
- **Search bar** (iOS `.searchable` in nav bar): runs `MKLocalSearch` on submit, drops olive pins for results, clears when search text is cleared
- **Detail card (bottom overlay):** tapping any pin shows place name, subtitle, and Google Maps deep-link
- Loads journal pins from `/api/map/pins`, caches them, uses cache offline

### Today (`TodayView`)
- Two-section `List` with paper background
- **Morning Guide:** stop cards showing serif place name + `HoursPill` + blurb + tip (Aegean-tinted background)
- **Evening Recap:** narrative text + list of visited entries with Maps links
- Offline banner (crimson) when showing cached data
- Section headers use `HodLabel` (uppercase mono)
- Pull-to-refresh, loads from `/api/today`

### Journey (`JourneyView`)
- Segmented picker: **Places** / **Insights**
- **Places:** list of all journaled entries; serif place name, sentiment emoji, one-line summary; taps into `EntryDetailView`
  - `EntryDetailView`: Nikos's summary, best/worst highlights (olive/crimson), Google Maps link or "unconfirmed" label
  - Top section: `FlowChips` showing Nikos has learned likes (olive) and dislikes (crimson)
- **Insights:** list of AI-generated insight cards with emoji, text, and tag
- Loads from `/api/places` and `/api/insights`

---

## Services

| Service | Role |
|---|---|
| `APIClient` | Thin async/await REST client; base URL and token read from `Info.plist`; throws `APIError.offline` on connection failure, `APIError.server(code)` on non-2xx |
| `CacheStore` | Simple `UserDefaults`-backed JSON cache; used by Today, Map, and Journey for offline fallback |
| `LocationManager` | `CLLocationManager` wrapper; exposes `coordinate` and `placeName` (reverse-geocoded); used for lat/lon in requests and the location chip in Ask |

---

## Data Models (what the app consumes from the backend)

| Model | Endpoint | Notes |
|---|---|---|
| `TodayResponse` | `/api/today` | `trip_day`, `date`, `region`, `morning_guide`, `evening_recap` |
| `MorningGuide` | ↑ | `stops[]`, `lunch` |
| `GuideStop` | ↑ | `name`, `hours`, `blurb`, `tip` |
| `EveningRecap` | ↑ | `narrative`, `entries[]` |
| `ChatResponse` | `/api/chat` | `reply`, `places[]`, `sources[]` |
| `Place` | Various | `place_id`, `name`, `address`, `lat`, `lon`, `category`, `rating`, `rating_count`, `maps_url` |
| `JournalStartResponse` | `/api/journal/start` | `entry_id`, `reply` |
| `JournalMessageResponse` | `/api/journal/message` | `reply`, `candidate` (Place?) |
| `PlacesResponse` | `/api/places` | `entries[]`, `preferences` |
| `JournalEntry` | ↑ | `id`, `place_name`, `sentiment`, `line`, `summary`, `best`, `worst`, `maps_url` |
| `Preferences` | ↑ | `likes[]`, `dislikes[]` |
| `InsightsResponse` | `/api/insights` | `insights[]` |
| `Insight` | ↑ | `id`, `emoji`, `text`, `tag` |
| `PinsResponse` | `/api/map/pins` | `pins[]` |
| `MapPin` | ↑ | `id`, `place_name`, `lat`, `lon`, `sentiment`, `line`, `maps_url` |

---

## What the app does NOT yet have (pending backend)

Per `BACKEND_REQUIREMENTS.md` in the project root:

- **Past conversations history** (Ask threads + Journal transcripts) — needs `/api/conversations` endpoints
- **Upcoming itinerary stops on Home** — needs `/api/itinerary` or enhanced `/api/today`
- **Nearby events on Home** — needs `/api/events`
- **Full AI context injection** — backend needs to read and use the `timestamp` field already being sent
- **AI-generated conversation summaries** — needed as titles for the history view
- **Journal discard endpoint** — low priority cleanup
