# Ὁδηγός — AI Travel Concierge & Journaling Agent

**Ὁδηγός** (Greek for "guide", *o-dhi-GOS*) is a voice-friendly iOS travel
companion built for a single-user V1 deployment: a 21-day spiritual &
historical tour of Greece (Sept 5–25). Its in-app assistant persona is
**Nikos**.

> **Naming convention.** `Ὁδηγός` is used wherever the user reads the name
> (app display name, docs, UI chrome). `Hodegos` is the Latin transliteration
> used for identifiers — module and file names, Info.plist keys, hostnames,
> service names, database and cache paths. `Nikos` is *only* the assistant
> persona: system prompts and assistant-facing copy like "Ask Nikos".

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

`backend/` is a working FastAPI scaffold (see `backend/README.md` to run it);
`ios/` holds the SwiftUI sources (see `ios/README.md` for Xcode setup);
`knowledge/` is live seed data starting with the trip itinerary. The full
system design is in `docs/architecture.md` and the build schedule in
`docs/plan.md`.

## App structure (V1)

Five tabs, decided via clickable UX prototype:

| Tab | Purpose |
|---|---|
| **Ask** | Concierge chat — text field + native iOS dictation, location chip, grounded answers |
| **Journal** | Feedback capture — place resolution with Yes/No confirmation, explicit Done to file an entry |
| **Map** | Orange pins for journaled places, blue pins for AI recommendations handed off from Ask |
| **Today** | Morning Guide (7 AM) and Evening Recap (8 PM) generated server-side |
| **Journey** | Two sections: Places (journal history, learned preferences, per-place summaries with Maps links) and Insights (daily digest job's trend cards about the trip) |

Plus a **Trip memory** toggle on the Ask tab: when on, answers come from RAG over
the entire trip archive (journal entries + past conversations) with source
citations, instead of itinerary-RAG + live search.

See `docs/decisions.md` for the scoping decisions and their rationale.
