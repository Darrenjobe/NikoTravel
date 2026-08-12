# Hodegos — Backend Requirements for Pending iOS Features

Generated from iOS client feedback review. Each item is tagged with the feature it unblocks.

---

## 1. Context injection in every AI prompt

**Feature:** Ask page — "context should be included with every prompt under the covers"

The iOS client already sends `timestamp` (ISO 8601) alongside the existing `lat` / `lon` fields on every `POST /api/chat` request. The backend needs to:

- Read the `timestamp` field from the request body.
- Inject a natural-language context block into the system prompt before the user message, e.g.:

  > "The user is currently in Athens, Greece (37.97°N, 23.73°E). The local time is 2:14 PM on Saturday, 9 August. Today is Day 3 of their trip."

- Also inject today's itinerary stops (see §2) and any recent journal entries if available.

**Request body change (already sent by client):**
```json
{
  "message": "...",
  "lat": 37.97,
  "lon": 23.73,
  "memory_mode": false,
  "timestamp": "2026-08-09T14:14:00+03:00"
}
```

---

## 2. Itinerary / planned stops data for the Home page

**Feature:** Home page — upcoming itinerary stops, planned attractions

The iOS client currently shows today's morning guide (`/api/today → morning_guide.stops`) on the home page if cached. To show *upcoming* planned stops across future days the backend needs either:

- Enhance `GET /api/today` to also return an `upcoming` array of stops for the next 1–2 days.
- Or add a new endpoint: `GET /api/itinerary` returning all planned days with stops, dates, and times.

**Suggested response shape:**
```json
{
  "days": [
    {
      "trip_day": 4,
      "date": "2026-08-10",
      "stops": [
        { "name": "Cape Sounion", "hours": "Opens 8 AM", "blurb": "...", "tip": "..." }
      ]
    }
  ]
}
```

---

## 3. Nearby special events and celebrations

**Feature:** Home page — "nearby special events or celebrations"

Needs a new endpoint that returns time-sensitive local events near the user's current location. Suggested sources: Google Places Events, Eventbrite, a manually curated list, or scraped local event calendars.

**Suggested endpoint:** `GET /api/events?lat=&lon=&radius_km=5`

```json
{
  "events": [
    {
      "title": "Athens Epidaurus Festival — evening performance",
      "date": "2026-08-09",
      "time": "21:00",
      "location": "Odeon of Herodes Atticus",
      "blurb": "Annual classical drama festival.",
      "url": "https://..."
    }
  ]
}
```

---

## 4. Past Ask conversations — list and full transcript

**Feature:** Conversations history tab (requested under "More" / sidebar)

The client wants a unified history screen showing all past chat threads with a concise title and the ability to drill into the full transcript.

**New endpoints needed:**

### `GET /api/conversations`
Returns all completed Ask conversations, most recent first.

```json
{
  "conversations": [
    {
      "id": "abc123",
      "type": "ask",
      "summary": "Discussed Byzantine history at Mystras and recommended tavernas near the site",
      "started_at": "2026-08-08T10:22:00Z",
      "message_count": 6
    }
  ]
}
```

- `summary` should be AI-generated when the conversation ends (or lazily on first retrieval). A single sentence or two describing what was discussed.
- `type` is `"ask"` for chat conversations.

### `GET /api/conversations/{id}`
Returns the full message thread.

```json
{
  "id": "abc123",
  "type": "ask",
  "summary": "...",
  "started_at": "2026-08-08T10:22:00Z",
  "messages": [
    { "role": "user", "text": "What's the history of Mystras?", "timestamp": "..." },
    { "role": "assistant", "text": "Mystras was a Byzantine fortress city...", "timestamp": "..." }
  ]
}
```

**Implementation note:** The backend needs to persist every message in the Ask thread (not just the final response). Currently it appears only the reply is returned to the client — the full thread must be stored server-side.

---

## 5. Past Journal conversations — full transcript per entry

**Feature:** Conversations history tab — "full journal conversation" per entry

Each `JournalEntry` (returned by `GET /api/places`) needs a retrievable full conversation transcript — the back-and-forth dialogue that led to the entry, not just the summary.

**New endpoint:**

### `GET /api/journal/{entry_id}/transcript`

```json
{
  "entry_id": "xyz789",
  "place_name": "Taverna Klimataria",
  "messages": [
    { "role": "user", "text": "Just had the best meal...", "timestamp": "..." },
    { "role": "assistant", "text": "That sounds wonderful! Was this near Monastiraki?", "timestamp": "..." }
  ]
}
```

**Implementation note:** Journal message threads must be stored server-side. Currently `journalMessage` returns a reply but it's unclear whether the full thread is persisted. Ensure every message and reply is stored against the `entry_id`.

---

## 6. Unified conversations feed with type filter

**Feature:** Toggle on history screen — "see all / just ask threads / just journal threads"

Extend `GET /api/conversations` to support a `type` query parameter:

- `GET /api/conversations` — all (ask + journal)
- `GET /api/conversations?type=ask` — only Ask chat threads
- `GET /api/conversations?type=journal` — only Journal entry conversations

Journal conversations should appear in this list with `type: "journal"` and the `place_name` as additional context, alongside the AI-generated `summary`.

---

## 7. AI-generated conversation summaries

**Feature:** History list — "concise generated summary about what was discussed as the title"

When an Ask conversation ends (either by the user navigating away or after a timeout), the backend should:

1. Pass the full message thread to the LLM with a prompt like: *"Summarize this travel conversation in one sentence, focusing on the specific topics and places discussed."*
2. Store the result as `summary` on the conversation record.
3. Return it in `GET /api/conversations`.

For Journal entries, a similar summary can be derived from the existing `summary` field on `JournalEntry` — but it should reflect the *conversation* not just the place, e.g. "Discussed the disappointing service at Taverna X and confirmed the location."

---

## 8. Discard / cancel an in-progress journal entry (optional)

**Feature:** Journal — "Discard" button on new entry alert

Currently if the user taps "Discard" on the new-entry confirmation, the iOS client clears local state but the backend entry (if `entry_id` was already created via `POST /api/journal/start`) is left in an incomplete state.

**Suggested endpoint:** `DELETE /api/journal/{entry_id}` or `POST /api/journal/discard`

```json
{ "entry_id": "xyz789" }
```

This is low priority — orphaned incomplete entries are harmless — but useful for keeping the backend clean.

---

## Summary table

| # | Feature | Endpoint(s) | Priority |
|---|---|---|---|
| 1 | AI context injection (time + itinerary) | Backend reads existing `timestamp` field | High |
| 2 | Upcoming itinerary stops on Home | `GET /api/itinerary` or enhance `/api/today` | High |
| 3 | Nearby events on Home | `GET /api/events?lat=&lon=` | Medium |
| 4 | Past Ask conversations list + transcript | `GET /api/conversations`, `GET /api/conversations/{id}` | High |
| 5 | Journal full transcripts | `GET /api/journal/{entry_id}/transcript` | High |
| 6 | Type filter on conversations feed | `?type=ask\|journal` param on `/api/conversations` | Medium |
| 7 | AI-generated conversation summaries | Background job when conversation ends | High |
| 8 | Discard in-progress journal entry | `DELETE /api/journal/{entry_id}` | Low |
