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
cp .env.example .env          # fill in keys
set -a; source .env; set +a
uvicorn app.main:app --reload
```

`app/__init__.py` enforces the minimum version, so a wrong interpreter fails
immediately with instructions rather than a misleading traceback.

First run:

```bash
TOKEN=$(grep API_TOKEN .env | cut -d= -f2)
curl -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/api/rebuild-index
curl -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/api/jobs/morning
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/today
```

## Deploy (Render)

1. Push this repo to GitHub (already done).
2. Render dashboard → **New → Blueprint** → point at the repo;
   `backend/render.yaml` defines the web service, disk, and three cron jobs.
3. Set the secret env vars when prompted (`API_TOKEN`, `ANTHROPIC_API_KEY`,
   `GOOGLE_PLACES_API_KEY`, `TAVILY_API_KEY`).
4. After the first deploy, hit `/api/rebuild-index` once to build the
   knowledge index (the itinerary ships inside the image; re-run after
   editing anything in `knowledge/`).

## Degradation behavior

- No `GOOGLE_PLACES_API_KEY` → journal skips place resolution (placeholder
  entries), chat recommendations have no pins.
- No `TAVILY_API_KEY` → the web_search tool reports it's unconfigured; the
  model answers from the itinerary and its own knowledge.
- No `ANTHROPIC_API_KEY` → set `LLM_PROVIDER=openai` + `OPENAI_API_KEY`
  (plain chat; no tool use or structured extraction in the fallback).
