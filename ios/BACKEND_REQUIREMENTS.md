# Hodegos — Backend Requirements

All items from the initial sprint are complete. The iOS client is fully wired up to every endpoint listed below.

## Completed ✅

| # | Feature | Endpoint(s) | iOS status |
|---|---|---|---|
| 1 | Context injection (timestamp + itinerary + journal) | `services/context.py` | Timestamp sent on every `/api/chat` request |
| 2 | Itinerary / upcoming stops | `GET /api/itinerary`, upcoming on `/api/today` | HomeView loads and displays upcoming days |
| 3 | Nearby events | `GET /api/events?lat=&lon=` | HomeView fetches and displays event cards |
| 4 | Conversations list + transcript | `GET /api/conversations`, `GET /api/conversations/{id}` | HistoryListView + ConversationThreadView in Journey tab |
| 5 | Journal transcripts | `GET /api/journal/{id}/transcript` | Wired in APIClient (ready for use) |
| 6 | `?type=` filter | `?type=ask\|journal` on `/api/conversations` | HistoryListView segmented filter |
| 7 | AI-generated summaries | Background job + fallback titles | Displayed as row titles in conversation list |
| 8 | Discard journal entry | `DELETE /api/journal/{id}` | Called on Journal "Discard" action |

## No current blockers

The frontend has no pending backend dependencies. Next sprint items should be driven by new product requirements.
