# Ὁδηγός backend

FastAPI + SQLite + ChromaDB. See `docs/architecture.md` for the design.

## Local dev

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in keys
set -a; source .env; set +a
uvicorn app.main:app --reload
```

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
