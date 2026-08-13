# Product & Architecture Decisions

Running log of decisions made while shaping the V1 prototype. Newest at the bottom.

## Scope (decided 2026-08-09)

- **Timeline:** trip starts Sept 5 (~4 weeks of runway from kickoff).
- **Voice:** native iOS dictation for input (no custom STT streaming pipeline in V1).
  TTS output is a possible fast-follow, not in the critical path.
- **All four features are must-have:** concierge Q&A, journaling, Morning Guide
  (7 AM), Evening Recap (8 PM).
- **Provisioned:** LLM API key. Still needed: Google Places/Maps key; speech APIs
  deferred with the dictation decision.

## UX (decided 2026-08-09, via clickable prototype)

- **Five tabs:** Ask / Journal / Map / Today / Places.
- **Mic interaction:** tap to start, tap to stop (not push-to-talk hold).
- **Visual direction:** utilitarian, native SwiftUI components.
- **Journal flow:** optional Google Maps link paste; otherwise Niko resolves the
  place from context + GPS and asks for Yes/No confirmation. "No" stores an
  "Unconfirmed location" placeholder. Explicit **Done** button files the entry
  and triggers summary generation; leaving mid-conversation autosaves a draft.
- **Map tab:** journaled places as orange pins; recommendations from Ask arrive
  as blue pins via a "Show these on the map" button in the answer bubble.
  Recommendation pins are ephemeral; journal pins are permanent.
  API contract implication: concierge responses return
  `{ answer_text, places[] }` where places carry name, Place ID, and coords.

## Journey tab & Trip memory (decided 2026-08-09)

- **"Places" tab renamed "Journey"**, split by a segmented control into:
  - **Places** — the existing filterable history of journaled places.
  - **Insights** — trend/fact cards about the trip ("you ate at 3 different
    Greek places today", "every site you've loved was a pre-10 AM visit").
- **Insights digest job (backend):** runs once or twice a day, but only when
  2+ interactions (journal entries, concierge Q&A, any conversations) occurred
  in the trailing 12–24 h. It analyzes that window's full interaction archive —
  journal entries AND concierge conversations — and emits fact cards. All
  conversations are archived to make this possible; the archive is the same
  corpus Trip memory searches.
- **Trip memory toggle (Ask tab):** a pill above the input bar. When ON, the
  backend flips retrieval priority to RAG over the entire trip archive
  (journal + past Q&A + conversations) instead of itinerary-RAG + live search.
  Answers in this mode cite their source (e.g. "📓 Journal · Sept 5 ·
  The Underdog"). Implementation note: this is a per-request flag in the chat
  API payload, not a separate endpoint.

## Naming (decided 2026-08-10)

The app is **Ὁδηγός** (Greek for "guide", *o-dhi-GOS*). Three names with three
distinct jobs — they are not interchangeable:

| Name | Used for | Examples |
|---|---|---|
| `Ὁδηγός` | Anything the user reads as the app's name | `CFBundleDisplayName`, permission strings, doc titles |
| `Hodegos` | Identifiers (Latin transliteration) | `ios/Hodegos/`, `HodegosApp.swift`, bundle ID, `HodegosBaseURL`/`HodegosAPIToken`, `hodegos-backend` on Render, `hodegos.db`, cache dir |
| `Niko` | The in-app assistant persona only | "Ask Niko", "What Niko's learned", the `.niko` chat role, backend system prompts |

Rationale: non-ASCII product/module names cause friction in bundle IDs,
schemes, hostnames, and CLI tooling, so Greek script is confined to display
strings. The persona keeps its own name — Niko is the guide *inside* Ὁδηγός.

Not renamed: the GitHub repo (`darrenjobe/nikotravel`) and its local checkout
path. Renaming the remote would break existing clones and the Render blueprint
link for no functional gain; it can be done later from GitHub settings if
desired.

## Architecture (decided 2026-08-09)

- **LLM:** Anthropic (Claude) primary via a swappable `services/llm.py`
  interface; OpenAI plain-chat fallback. Models per role via env
  (`CHAT_MODEL`/`JOB_MODEL`, default `claude-sonnet-5`). Both are overridable
  at runtime via `POST /api/models`, which persists to SQLite and wins over
  the env vars — so the model can be changed from the phone mid-trip without
  a redeploy.
- **Hosting:** Render.com (Frankfurt) — Docker web service + 5GB persistent
  disk + three cron jobs that curl the job endpoints.
- **Maps:** Apple MapKit in-app; Google Places API server-side for entity
  resolution and recommendations; deep links out to Google Maps.
- **Live search:** Tavily free tier, invoked as a model tool (not on every
  request).
- **Auth:** single static bearer token on all routes.
- **Storage:** SQLite (system of record) + ChromaDB (`knowledge` and
  `archive` collections) on the persistent disk.
- Full design: `docs/architecture.md`. Schedule: `docs/plan.md`.

## Known open questions

- Map when history spans multiple regions (the trip covers ~10): auto-fit bounds
  vs. region picker.
- Google Maps iOS SDK vs. Apple MapKit + Places data. Leaning Google SDK to keep
  Place IDs consistent end-to-end.
- Recommendation pin persistence between sessions.
- **Mt Athos (Sept 20–23): 4 days of minimal connectivity.** The app must
  pre-cache the day's guide and degrade gracefully offline — concierge and
  journaling both need an offline story (queue journal entries locally, sync on
  reconnect).
- Itinerary inconsistencies to resolve before the trip: Patmos listed as an
  Athens "daytrip" (Piraeus–Patmos is an 7–8 hr ferry each way); Veria and
  Kavala/Philippi have destination profiles but no days allocated in the
  overview table.
