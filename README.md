# Project Niko — AI Travel Concierge & Journaling Agent

Niko is a voice-friendly iOS travel companion built for a single-user V1 deployment:
a 21-day spiritual & historical tour of Greece (Sept 5–25).

Two core jobs:

1. **On-demand concierge** — answer questions about historical sites, food, transit,
   hours, and lodging in the moment, grounded in the user's own itinerary and notes
   (RAG) plus live web search.
2. **Conversational journaling** — capture feedback about places just visited,
   resolve them to real Google Places entries, and feed the results back into
   future recommendations.

## Repo layout

```
knowledge/        The user's "brain" — Markdown files synced to the backend and
                  embedded into the RAG index (itinerary, notes, journal output)
ios/              SwiftUI client (thin: dictation input, GPS context, chat UI)
backend/          FastAPI orchestrator (LLM, entity resolution, RAG, cron reports)
docs/             Architecture and product decisions
```

`ios/` and `backend/` are scaffolded as the build progresses; `knowledge/` is live
seed data starting with the trip itinerary.

## App structure (V1)

Five tabs, decided via clickable UX prototype:

| Tab | Purpose |
|---|---|
| **Ask** | Concierge chat — text field + native iOS dictation, location chip, grounded answers |
| **Journal** | Feedback capture — place resolution with Yes/No confirmation, explicit Done to file an entry |
| **Map** | Orange pins for journaled places, blue pins for AI recommendations handed off from Ask |
| **Today** | Morning Guide (7 AM) and Evening Recap (8 PM) generated server-side |
| **Places** | Journal history, learned preferences, per-place summary with Google Maps link |

See `docs/decisions.md` for the scoping decisions and their rationale.
