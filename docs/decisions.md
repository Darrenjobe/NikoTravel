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
