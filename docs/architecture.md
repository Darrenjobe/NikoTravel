# Ὁδηγός — V1 Architecture (Final)

App name **Ὁδηγός** (identifiers use the transliteration `Hodegos`); **Nikos**
is the in-app assistant persona.

Single-user deployment for the Greece trip (Sept 5–25). Optimized for: reliable on
a phone over eSIM data, cheap to run, buildable solo in ~4 weeks, degradable when
offline (Mt Athos).

## System overview

```
┌─────────────────────────┐         HTTPS (JSON)          ┌──────────────────────────────┐
│  iOS app (SwiftUI)      │ ────────────────────────────▶ │  Backend (FastAPI on Render)  │
│                         │                               │                              │
│  · 5 tabs               │   POST /api/chat              │  · Chat orchestrator          │
│  · native dictation     │   POST /api/journal/*         │  · Journal + place resolution │
│  · CoreLocation (GPS)   │   GET  /api/today             │  · RAG (ChromaDB)             │
│  · MapKit               │   GET  /api/places            │  · SQLite (structured data)   │
│  · local cache of Today │   GET  /api/insights          │  · Jobs: morning/evening/     │
│    + queued journal     │   GET  /api/map/pins          │    insights (cron)            │
│    entries (offline)    │   POST /api/jobs/{name}       │                              │
└─────────────────────────┘                               └──────┬───────────────────────┘
                                                                 │
                                            ┌────────────────────┼──────────────────┐
                                            ▼                    ▼                  ▼
                                      Anthropic API        Google Places       Tavily Search
                                      (Claude; OpenAI      (entity resolution, (live hours,
                                       swappable)           Maps links)         weather, transit)
```

## Decisions (locked)

| Area | Choice | Notes |
|---|---|---|
| LLM | Claude via Anthropic SDK, default `claude-sonnet-5`; swappable interface, OpenAI fallback available | Per role via env (`CHAT_MODEL`, `JOB_MODEL`), overridable at runtime through `POST /api/models` |
| Hosting | Render.com — one Docker web service + persistent disk + cron jobs | Frankfurt region (closest to Greece) |
| Data | SQLite (entries, conversations, insights) + ChromaDB (embeddings) on the persistent disk | No managed DB for one user |
| Maps | Apple MapKit in-app; Google Places API server-side for entity resolution; deep links out to Google Maps | No Google SDK in the iOS app |
| Live search | Tavily (free tier, 1,000/mo) | Only invoked when the model asks for it (tool use) |
| Voice | Native iOS keyboard dictation for input | No STT service; TTS deferred |
| Auth | Single static bearer token (`API_TOKEN`) checked on every route | Sufficient for one user; rotate if leaked |

## Backend

FastAPI app, Python 3.12, Dockerized. Layout:

```
backend/
  app/
    main.py            FastAPI app, router mounting, auth dependency
    config.py          env-driven settings
    routers/
      chat.py          POST /api/chat  (concierge; memory_mode flag)
      journal.py       POST /api/journal/* (start, message, confirm, finish)
      today.py         GET  /api/today
      journey.py       GET  /api/places, /api/insights
      map.py           GET  /api/map/pins, /api/places/search
      saved.py         GET/POST /api/saved, DELETE /api/saved/{place_id}
      models.py        GET/POST/DELETE /api/models (in-app model switching)
      admin.py         POST /api/rebuild-index, POST /api/jobs/{name}
    services/
      llm.py           LLM interface; AnthropicLLM (default) / OpenAILLM
      rag.py           ChromaDB index over knowledge/ + archive
      places.py        Google Places text search + place details
      search.py        Tavily web search
      tripday.py       date → trip-day/region mapping from the itinerary
      settings.py      runtime overrides for env config (model selection)
      models.py        Anthropic Models API catalog, cached 24h in SQLite
      tts.py           ElevenLabs speech; markdown stripping + disk cache
      gdrive.py        Google Drive REST (OAuth refresh token)
      archive.py       stores every conversation turn (chat + journal)
    storage/
      db.py            SQLite schema + helpers
    jobs/
      morning.py       Morning Guide generation
      evening.py       Evening Recap compilation
      insights.py      Insight digest (conditional: 2+ interactions/24h)
      backup.py        Hourly incremental push of the archive to Drive
  Dockerfile
  requirements.txt
  (render.yaml lives at the repo root — Render only reads it from there)
  .env.example
```

### The chat flow (Ask tab)

1. Client sends `{message, lat, lon, memory_mode}`.
2. Server builds the system prompt: persona + today's trip context (from
   `tripday`) + retrieved snippets. Retrieval source depends on `memory_mode`:
   - off → itinerary/knowledge collection
   - on  → full-trip archive collection (journal + past conversations), and the
     response cites sources
3. Claude is called with two tools: `web_search` (Tavily — hours, weather,
   transit) and `recommend_places` (Google Places — structured results). Manual
   tool loop, max 3 iterations.
4. Response: `{reply, places[], sources[]}`. `places[]` (name, place_id, lat,
   lon, maps_url, note) drives the "Show on map" handoff in the client.
5. The full turn is archived (SQLite + embedded into the archive collection).

### The journal flow

1. `start` creates a draft entry (optional pasted Maps link short-circuits
   resolution).
2. Each `message` runs entity resolution when no place is attached yet:
   transcript + GPS → Google Places text search → candidate returned for
   Yes/No confirmation.
3. `confirm` attaches the place or records the "unconfirmed" placeholder.
4. `finish` runs structured extraction (Claude, JSON schema output): rating
   sentiment, best/worst, summary, preference signals (likes/dislikes). Stored
   in SQLite, embedded into the archive collection, preferences merged into the
   profile table.

### Jobs (Render cron)

| Job | Schedule (UTC) | What it does |
|---|---|---|
| morning | `0 4 * * *` (7am EEST) | Looks up today's region, researches each planned site (Tavily), writes the Morning Guide to SQLite |
| evening | `0 17 * * *` (8pm EEST) | Compiles the day's journal summaries into the Evening Recap |
| insights | `0 11,20 * * *` | If 2+ interactions in trailing 24h: analyze archive window, emit insight cards |
| backup | `0 * * * *` (hourly) | Pushes new/changed journal entries and transcripts to Google Drive; content-hashed, so a quiet hour uploads nothing |
| summarize | on demand | Titles for the conversation history. Normally runs as a background task scheduled by `GET /api/conversations`, so no cron service is needed; `POST /api/jobs/summarize` forces it |

### Conversation threading

`POST /api/chat` without a `conversation_id` opens a thread and returns its id;
sending that id back continues the thread. Prior turns are replayed to the
model, so follow-ups ("what about tomorrow?") resolve against what was already
said — before this, every message was answered in isolation.

Journal threads reuse the entry id as the thread id, so one entry is a journal
record and a conversation from two angles with no extra state. Both kinds
surface in `GET /api/conversations`.

Summaries are generated once a thread has been quiet for 10 minutes, not after
every message. Until then the list shows the first user message, trimmed — so
a title is always present, and `summary_is_ai` tells the client which it is.

### Ambient context injection

Every chat request builds a context block (`services/context.py`) from the
client's `timestamp` and GPS plus server-side state: local time and trip day,
current region, today's planned sites and dining options from the itinerary, a
heads-up when tomorrow changes region, learned preferences, and recent journal
verdicts. The system prompt states the traveler should never be asked for any
of it.

Cron jobs are thin `curl` calls to `POST /api/jobs/{name}` with the bearer
token, so job code lives in the same deploy and can also be triggered manually
from the phone (pull-to-refresh).

### Offline strategy (Mt Athos, ferries)

- Client caches the latest `/api/today` payload and the full Places list on
  device; tabs render from cache when offline.
- Journal entries compose offline and queue; a background task syncs when
  connectivity returns.
- Ask shows a clear offline state (no fake answers).
- Before Sept 20, morning guides for the Athos days are pre-generated so the
  cache has them.

## iOS app

SwiftUI, iOS 17+, no third-party dependencies. Layout:

```
ios/Hodegos/
  HodegosApp.swift         entry point
  ContentView.swift        TabView (Ask / Journal / Map / Today / Journey)
  Models/Models.swift      Codable API models
  Services/
    APIClient.swift        async/await client, bearer token, base URL
    LocationManager.swift  CoreLocation wrapper (coarse updates)
    CacheStore.swift       JSON file cache + offline journal queue
  Views/
    AskView.swift          chat UI, memory toggle, starter prompts
    JournalView.swift      feedback chat, place-confirm card, Done flow
    MapView.swift          MapKit map, journal pins + recommendation pins
    TodayView.swift        Morning Guide + Evening Recap
    JourneyView.swift      Places list + Insights (segmented)
```

Input: standard text field — the iOS keyboard's built-in dictation button
covers voice input with zero code and zero permissions. Location: "when in use"
authorization, coarse accuracy is fine.

## API contract (summary)

All routes require `Authorization: Bearer <API_TOKEN>`.

| Route | Body → Response |
|---|---|
| `POST /api/chat` | `{message, lat?, lon?, memory_mode, timestamp?, conversation_id?}` → `{reply, places[], sources[], conversation_id}` |
| `GET /api/conversations?type=ask\|journal` | → `{conversations[]}` (unified Ask + Journal feed) |
| `GET /api/conversations/{id}` | → thread metadata + `messages[]` |
| `GET /api/journal/{entry_id}/transcript` | → `{entry_id, place_name, messages[]}` |
| `DELETE /api/journal/{entry_id}` | discard a draft (409 if already filed) |
| `GET /api/itinerary?days=&start=` | → `{days[]}` with stops + dining per day |
| `GET /api/events?lat=&lon=&radius_km=` | → `{events[]}` (12h cached per region) |
| `POST /api/journal/start` | `{maps_link?}` → `{entry_id, reply}` |
| `POST /api/journal/message` | `{entry_id, message, lat?, lon?}` → `{reply, candidate?}` |
| `POST /api/journal/confirm` | `{entry_id, accepted}` → `{reply}` |
| `POST /api/journal/finish` | `{entry_id}` → `{entry}` (full stored entry) |
| `GET /api/today` | → `{trip_day, region, morning_guide?, evening_recap?, upcoming[]}` |
| `GET /api/places` | → `{entries[], preferences}` |
| `GET /api/insights` | → `{insights[]}` |
| `GET /api/map/pins` | → `{pins[]}` (journal places with coords) |
| `GET /api/places/search?q=&lat=&lon=&n=` | → `{places[]}` from Google Places, with real Place IDs |
| `GET /api/saved` | → `{places[]}` hearted on the Map tab, newest first |
| `POST /api/saved` | a place object → `{ok, saved: true}` (idempotent) |
| `DELETE /api/saved/{place_id}` | → `{ok, saved: false}` (no-op if absent) |
| `GET /api/models?refresh=&all=` | → `{models[], source, chat_model, job_model}` (24h cache) |
| `GET /api/models/current` | → the selection only, no network call |
| `POST /api/models` | `{chat_model?, job_model?}` → persists the choice |
| `DELETE /api/models` | reset to the `CHAT_MODEL`/`JOB_MODEL` env defaults |
| `POST /api/tts` | `{text, voice_id?, model_id?}` → **`audio/mpeg` bytes**, not JSON |
| `POST /api/tts/preview` | → the cleaned text that would be spoken; spends no credits |
| `GET /api/tts/voices` | → `{voices[]}` from the ElevenLabs account |
| `POST /api/jobs/{morning\|evening\|insights}` | → job result |
| `POST /api/rebuild-index` | → re-index knowledge/ into ChromaDB |

## Hosting choice — why Render/Frankfurt, and why region barely matters

**Decision: keep Render, `region: frankfurt`.** Already in `render.yaml`.

The instinct is to minimize physical distance to Greece. But the network hop
to the host is a rounding error next to LLM inference. Rough round-trip times
from a Greek mobile network, versus what a concierge answer actually costs:

| Leg | Approx. time |
|---|---|
| Phone → Frankfurt | ~40–60 ms |
| Phone → Milan / Ireland | ~45–80 ms |
| Phone → US East | ~130–180 ms |
| **LLM inference for one grounded answer (with tool calls)** | **5,000–25,000 ms** |

Even the worst geography adds ~120 ms to a ~15 s request — under 1%. Choosing
a host by map distance optimizes the wrong term. Frankfurt is picked because
it's a well-peered hub that Greek carriers route through anyway, not because
those milliseconds are decisive.

**What actually determines whether this feels fast on the ground:**

1. **No cold starts.** A spun-down instance costs 30–60 s on the first
   request — worse than every geography decision combined. The blueprint uses
   `plan: standard` for exactly this reason. Do **not** downgrade to a
   free/spin-down tier before the trip.
2. **Model and effort on the chat path.** This is the real latency dial. If
   answers feel slow, drop `CHAT_MODEL` to `claude-haiku-4-5`, or lower
   `effort` — both are env vars, changeable from the Render dashboard mid-trip
   without a redeploy.
3. **Streaming the reply** (not yet implemented). The largest perceived-speed
   win available: first tokens in ~1–2 s instead of a blank screen for 15 s.
   Worth doing in week 3 if time allows.
4. **Generous client timeouts.** The iOS client uses 60 s; a tool-using answer
   on a weak signal can legitimately take 20–30 s. Verify long requests
   survive the platform's own proxy timeout before departure.

**Alternatives considered:** Fly.io (cheaper, closer edge regions, but
CLI-heavy and volumes are region-pinned), Hetzner (far cheaper, but you own
nginx/TLS/systemd/backups — wrong risk profile weeks before a trip), Azure
Greece Central (nominally closest, disproportionate setup). None of them buy
enough to justify re-plumbing a working deploy.

**The real Greece risks are not latency:** Mt Athos has no signal at all
(handled by offline caching, §Offline strategy), ferries drop connectivity
mid-crossing, and roaming data caps make response size worth watching. Those
are client-side problems, not hosting ones.

## Cost estimate (trip month)

| Item | Est. |
|---|---|
| Render Standard + disk | ~$25 |
| Claude API (chat + jobs, ~50 interactions/day) | $10–30 |
| Google Places (entity resolution, ~10/day) | ~$0 (free credit) |
| Tavily | $0 (free tier) |
| **Total** | **~$35–55 for the trip** |
