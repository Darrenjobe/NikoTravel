# Ὁδηγός backend

FastAPI + SQLite + ChromaDB. See `docs/architecture.md` for the design.

## Requirements

**Python 3.11+ — 3.12 recommended** (production runs `python:3.12-slim`).

⚠️ **macOS:** the Command Line Tools ship Python **3.9**, which is too old —
`python3 -m venv` picks it up by default and the app fails at import with a
confusing Pydantic error (`Unable to evaluate type annotation 'float | None'`).
The annotations are fine; PEP 604 unions just need 3.10+. Install a newer
interpreter and build the venv from it explicitly:

```bash
brew install python@3.12
python3.12 --version          # confirm it's on PATH
```

## Local dev

```bash
cd backend
python3.12 -m venv .venv      # be explicit; don't rely on `python3`
source .venv/bin/activate
python --version              # must be 3.11+ before continuing
pip install -r requirements.txt

cp .env.example .env
openssl rand -hex 32          # paste as API_TOKEN=... in .env, then add your keys

uvicorn app.main:app --reload
```

`backend/.env` is loaded automatically at import — you do **not** need to
`source` it, and it works from any terminal tab. Real environment variables
always take precedence, so Render's dashboard config is never shadowed.

On startup the server logs exactly what it loaded:

```
Ὁδηγός config — .env found at /path/to/backend/.env
  ✓ API_TOKEN
  ✓ ANTHROPIC_API_KEY
  ✗ GOOGLE_PLACES_API_KEY
  ✗ TAVILY_API_KEY
```

If a route returns **503 "API_TOKEN is not set"**, check that line: either
`.env` wasn't found where the server looked, or `API_TOKEN` is blank in it.
`app/__init__.py` separately enforces the Python minimum, so a wrong
interpreter fails immediately with instructions rather than a misleading
Pydantic traceback.

First run:

```bash
# -f2- (not -f2) so a token containing '=' isn't truncated
TOKEN=$(grep '^API_TOKEN=' .env | cut -d= -f2-)
curl -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/api/rebuild-index
curl -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/api/jobs/morning
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/today
```

## The knowledge base (itinerary and notes)

Everything the concierge knows about the trip lives in `knowledge/` as
Markdown. The itinerary is already there:

```
knowledge/itinerary/greece-spiritual-historical-tour.md
```

It is read **two different ways**, which matters when you edit it:

| Path | Feeds | How it's read |
|---|---|---|
| Chroma index | Concierge answers (RAG) | Chunked on `/api/rebuild-index` |
| Direct parsing | `/api/today`, `/api/itinerary`, the injected context, morning guides | Overview table → dates/regions; `* **Name:** blurb` bullets → stops; dining tables → meal options |

**After any edit, run one command:**

```bash
scripts/job.sh reindex
```

That re-chunks the index *and* clears the parsed-itinerary caches, so changes
take effect immediately — no restart. It reports back what it found:

```json
{"indexed_chunks": 11, "files": ["itinerary/greece-...md"],
 "itinerary_found": true, "trip_days_parsed": 21}
```

Check `trip_days_parsed` — if it's 0 or wrong, the overview table stopped
parsing (see Format rules below).

### Adding more files

Any `.md` anywhere under `knowledge/` is indexed automatically — no config, no
code change. Useful additions:

```
knowledge/notes/bookings.md        hotel/ferry confirmations
knowledge/notes/preferences.md     dietary needs, mobility, what you care about
knowledge/notes/contacts.md        guides, drivers, emergency numbers
```

Then `scripts/job.sh reindex`. These are retrieved by the concierge but not
parsed structurally — only the itinerary drives dates and stops.

### Format rules (itinerary only)

The structural parsing depends on the existing shape. Keep these intact:

- **Overview table** rows of `| Region | N Days | Sept 5-7 |` — drives
  date→region mapping. Month abbreviations and `5-7` / `15` ranges both work.
- **`### Key Sites & Activities`** followed by `* **Name:** description`
  bullets — becomes `stops[]`.
- **Dining tables** with a `**Breakfast**` / `**Lunch**` / `**Dinner**` first
  cell — becomes `dining[]`.

Renaming the itinerary file is safe: the loader falls back to the first `.md`
in `knowledge/itinerary/`, and `ITINERARY_FILE` can point anywhere.

### In production

`knowledge/` is baked into the Docker image, so on Render the loop is:
edit → commit → push → Render redeploys → then
`HODEGOS_BASE=https://... scripts/job.sh reindex`. The redeploy ships the new
file; the reindex makes the server use it.

## Running the jobs by hand

In production Render's cron services just `curl` these endpoints — locally you
call them yourself. `scripts/job.sh` reads the token from `.env` for you:

```bash
scripts/job.sh reindex      # rebuild the knowledge index (run this first)
scripts/job.sh morning      # Morning Guide for today
scripts/job.sh evening      # Evening Recap from today's journal entries
scripts/job.sh insights     # Insight cards for the Journey tab
scripts/job.sh summarize    # Titles for the conversation history
```

Two jobs have thresholds that make them do nothing on a quiet test database.
Override them while testing (production never passes these):

```bash
scripts/job.sh 'insights?force=true'    # ignore the "2+ interactions in 24h" rule
scripts/job.sh 'insights?hours=72'      # widen the lookback window
scripts/job.sh 'summarize?force=true'   # don't wait 10 min for threads to go idle
```

`force` overrides a threshold, not reality — with an empty archive `insights`
still skips rather than asking the model to analyze nothing.

Point the script at the deployed service instead of localhost with:

```bash
HODEGOS_BASE=https://hodegos-backend.onrender.com scripts/job.sh morning
```

Raw equivalent, if you'd rather not use the script:

```bash
TOKEN=$(grep '^API_TOKEN=' .env | cut -d= -f2-)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  'localhost:8000/api/jobs/insights?force=true'
```

## Switching models without a redeploy

`CHAT_MODEL` and `JOB_MODEL` in `.env` are the defaults. The app can override
them at runtime — useful on the ground when API spend looks higher than
expected, or when a question deserves a bigger model:

```bash
TOKEN=$(grep '^API_TOKEN=' .env | cut -d= -f2-)
H="Authorization: Bearer $TOKEN"

curl -s -H "$H" localhost:8000/api/models              # what's available
curl -s -H "$H" 'localhost:8000/api/models?refresh=true'   # skip the 24h cache

curl -s -X POST -H "$H" -H 'Content-Type: application/json' \
  -d '{"chat_model":"claude-haiku-4-5"}' localhost:8000/api/models

curl -s -X DELETE -H "$H" localhost:8000/api/models    # back to the .env defaults
```

Chat and jobs are set independently — the concierge is latency-sensitive on
the ground, the overnight jobs are not. The override lives in SQLite, so it
survives restarts and redeploys; `DELETE` removes it and the env var applies
again.

The catalog comes from Anthropic's Models API and is cached for 24 hours. The
response's `source` field says where the list came from — `live`, `cache`,
`stale-cache` (refresh failed, serving the last good copy), or `fallback` (no
key or no connection, showing a small built-in list). Models that can't do
structured outputs are hidden, because journal extraction needs them; add
`?all=true` to see them and why they were excluded.

**Pricing is not in the response** — the Models API doesn't return it, and
hardcoding rates would go stale silently. Check current pricing on Anthropic's
pricing page.

## Speaking a response (ElevenLabs)

`POST /api/tts` turns any text the app is showing — an Ask answer, a journal
reply, a recommendation, the morning guide — into MP3 audio. It returns
**audio bytes, not JSON**:

```bash
curl -s -X POST -H "$H" -H 'Content-Type: application/json' \
  -d '{"text":"Καλημέρα! Today we visit the **Ἀκρόπολις**."}' \
  localhost:8000/api/tts --output reply.mp3 -D -
```

Check the `X-Hodegos-Cached` response header: `0` means it cost credits, `1`
means it came from the disk cache. Identical text is only ever synthesized
once.

**Markdown is stripped before synthesis**, because a speech engine reads `**`
and bullet characters aloud. Greek script is deliberately kept — the default
voice is a Greek speaker, and the Greek characters are what produce correct
pronunciation. Emoji are removed; the pattern that removes them explicitly
avoids the Greek Extended block, where `Ὁδηγός` itself lives.

See exactly what the voice will be given, without spending anything:

```bash
curl -s -X POST -H "$H" -H 'Content-Type: application/json' \
  -d '{"text":"## Stops\n* **Πλάκα** — the old quarter 🏛️"}' \
  localhost:8000/api/tts/preview
# {"spoken_text":"Stops\nΠλάκα — the old quarter", ...}
```

`GET /api/tts/voices` lists the account's voices if you want a different one.

**Voice id and model id are different fields.** The 20-character
`QnPbsq4pmOZkrE4RQQCA` is the *voice*; `eleven_flash_v2_5` is the *model*.
Passing a voice id as `model_id` is rejected by the API.

Without `ELEVENLABS_API_KEY` the endpoint returns **503** and everything else
keeps working. A failure from ElevenLabs itself returns **502** with their
reason attached, so a quota problem doesn't look like a bug.

## Testing from your phone (same Wi-Fi)

`127.0.0.1` is loopback — only the Mac itself can reach it. Bind to all
interfaces instead:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Find how the phone should address the Mac:

```bash
ipconfig getifaddr en0        # Wi-Fi IP, e.g. 192.168.1.42
scutil --get LocalHostName    # Bonjour name, e.g. Johns-MacBook-Pro
```

**Prefer the Bonjour name** (`http://Johns-MacBook-Pro.local:8000`) over the
raw IP: DHCP reassigns the IP whenever you rejoin the network, and the `.local`
name keeps working. It also satisfies iOS App Transport Security more cleanly
(see `ios/README.md`).

Verify from the phone's browser **before** touching the app — this separates
network problems from app problems. `/healthz` needs no token:

```
http://Johns-MacBook-Pro.local:8000/healthz   →   {"ok":true}
```

If that fails:

- **macOS firewall** — System Settings → Network → Firewall. If it's on,
  allow incoming connections for Python when prompted (the dialog can appear
  behind other windows).
- **Same network?** The phone must be on the same Wi-Fi, not cellular.
- **Client isolation** — many guest/public networks block device-to-device
  traffic entirely. Use a home network or a personal hotspot.

> ⚠️ `--host 0.0.0.0` exposes the API to everyone on that network. It's bearer
> token–protected, but don't run it that way on café or hotel Wi-Fi — keep it
> to your home network, or deploy to Render and use the real URL.

## Deploy (Render)

**Full runbook with verification steps: [`docs/deploy.md`](../docs/deploy.md).**

Short version: `render.yaml` at the **repo root** defines all four services
(web + three cron). Render dashboard → **New → Blueprint** → pick the repo and
branch → paste the secrets it prompts for → Apply. Then run
`POST /api/rebuild-index` once, or every answer will be ungrounded.

## Degradation behavior

- No `GOOGLE_PLACES_API_KEY` → journal skips place resolution (placeholder
  entries), chat recommendations have no pins.
- No `TAVILY_API_KEY` → the web_search tool reports it's unconfigured; the
  model answers from the itinerary and its own knowledge.
- No `ANTHROPIC_API_KEY` → set `LLM_PROVIDER=openai` + `OPENAI_API_KEY`
  (plain chat; no tool use or structured extraction in the fallback).
